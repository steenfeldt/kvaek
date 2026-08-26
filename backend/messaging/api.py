from datetime import datetime

from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from campaigns.models import Deal

from .models import Message, Review

router = Router(tags=["messaging"], auth=django_auth)


def _deal_for_user(request, deal_id: int) -> Deal:
    deal = Deal.objects.select_related("brief__campaign__brand__user", "brief__creator__user").filter(
        id=deal_id
    ).first()
    if deal is None:
        raise HttpError(404, "Deal not found")
    participants = {deal.brief.campaign.brand.user_id, deal.brief.creator.user_id}
    if request.user.id not in participants:
        raise HttpError(404, "Deal not found")
    return deal


class MessageOut(Schema):
    id: int
    sender_id: int
    mine: bool = False
    body: str
    created_at: datetime


@router.get("/deals/{deal_id}/messages", response=list[MessageOut])
def list_messages(request, deal_id: int, after_id: int = 0):
    deal = _deal_for_user(request, deal_id)
    qs = deal.messages.filter(id__gt=after_id)
    # Mark the other side's messages as read on fetch.
    qs.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
    return [
        MessageOut(id=m.id, sender_id=m.sender_id, mine=m.sender_id == request.user.id, body=m.body, created_at=m.created_at)
        for m in deal.messages.filter(id__gt=after_id)
    ]


class MessageIn(Schema):
    body: str


@router.post("/deals/{deal_id}/messages", response=MessageOut)
def send_message(request, deal_id: int, payload: MessageIn):
    deal = _deal_for_user(request, deal_id)
    body = payload.body.strip()
    if not body:
        raise HttpError(422, "Message is empty")
    m = Message.objects.create(deal=deal, sender=request.user, body=body)
    return MessageOut(id=m.id, sender_id=m.sender_id, mine=True, body=m.body, created_at=m.created_at)


class ReviewIn(Schema):
    rating: int
    text: str = ""


@router.post("/deals/{deal_id}/reviews")
def leave_review(request, deal_id: int, payload: ReviewIn):
    deal = _deal_for_user(request, deal_id)
    if not deal.completed:
        raise HttpError(409, "Both parties must mark the deal completed before reviewing")
    if not 1 <= payload.rating <= 5:
        raise HttpError(422, "Rating must be 1-5")
    if deal.reviews.filter(author=request.user).exists():
        raise HttpError(409, "Already reviewed")
    Review.objects.create(deal=deal, author=request.user, rating=payload.rating, text=payload.text.strip())
    return {"ok": True}
