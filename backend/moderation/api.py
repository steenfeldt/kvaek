from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from accounts.models import CreatorProfile
from campaigns.models import Deal

from .models import Report

router = Router(tags=["moderation"], auth=django_auth)


class ReportIn(Schema):
    reason: str
    creator_id: int | None = None
    deal_id: int | None = None


@router.post("/reports")
def create_report(request, payload: ReportIn):
    reason = payload.reason.strip()
    if not reason:
        raise HttpError(422, "Reason is required")
    if payload.deal_id is not None:
        deal = Deal.objects.select_related("brief__campaign__brand__user", "brief__creator__user").filter(
            id=payload.deal_id
        ).first()
        if deal is None:
            raise HttpError(404, "Deal not found")
        brand_user = deal.brief.campaign.brand.user
        creator_user = deal.brief.creator.user
        if request.user == brand_user:
            reported = creator_user
        elif request.user == creator_user:
            reported = brand_user
        else:
            raise HttpError(404, "Deal not found")
    elif payload.creator_id is not None:
        creator = CreatorProfile.objects.select_related("user").filter(id=payload.creator_id).first()
        if creator is None:
            raise HttpError(404, "Creator not found")
        reported = creator.user
    else:
        raise HttpError(422, "Nothing to report")
    if reported == request.user:
        raise HttpError(422, "Cannot report yourself")
    Report.objects.create(reporter=request.user, reported_user=reported, reason=reason)
    return {"ok": True}
