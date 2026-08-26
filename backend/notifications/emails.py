"""Transactional emails for the key events: brief received, proposal received,
deal made. Sent after commit; a mail failure must never break the transaction."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string


def _send(template: str, to: str, context: dict) -> None:
    context = {**context, "frontend_url": settings.FRONTEND_URL}
    subject = render_to_string(f"notifications/{template}_subject.txt", context).strip()
    text = render_to_string(f"notifications/{template}_body.txt", context)
    html = render_to_string(f"notifications/{template}_body.html", context)

    def deliver():
        message = EmailMultiAlternatives(subject, text, None, [to])
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=not settings.DEBUG)

    transaction.on_commit(deliver)


def brief_received(brief) -> None:
    _send("brief_received", brief.creator.user.email, {"brief": brief})


def proposal_received(proposal) -> None:
    brief = proposal.brief
    if proposal.author == "creator":
        to = brief.campaign.brand.user.email
    else:
        to = brief.creator.user.email
    _send(
        "proposal_received",
        to,
        {"proposal": proposal, "brief": brief, "amount_kr": proposal.amount_ore // 100},
    )


def waitlist_invite(entry, code: str) -> None:
    _send("waitlist_invite", entry.email, {"entry": entry, "code": code})


def deal_created(deal) -> None:
    brief = deal.brief
    context = {"deal": deal, "brief": brief, "amount_kr": deal.agreed_amount_ore // 100}
    _send("deal_created", brief.creator.user.email, {**context, "counterpart": brief.campaign.brand.company_name})
    _send("deal_created", brief.campaign.brand.user.email, {**context, "counterpart": brief.creator.display_name})
