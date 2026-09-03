"""Right-of-erasure and data-portability routines (GDPR art. 17 & 20).

Erasure anonymizes rather than deletes where financial records are involved:
Danish bookkeeping law requires keeping payment records ~5 years, so the
financial skeleton (campaigns, payments, deal amounts) survives with the
identity stripped. Chat messages written by the erased user are kept as part
of the counterparty's correspondence (defense of legal claims); the sender
identity behind them is anonymized.
"""

from django.contrib.sessions.models import Session
from django.db import transaction

from .models import User


@transaction.atomic
def erase_user(user: User) -> str:
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount

    from billing.models import Payment

    summary = []

    creator = getattr(user, "creator_profile", None)
    if creator is not None:
        for photo in creator.photos.all():
            photo.image.delete(save=False)
        for vr in creator.verification_requests.all():
            vr.evidence.delete(save=False)
        creator.delete()  # cascades photos, social links, briefs, deals, messages, reviews
        summary.append("creator profile deleted (incl. files)")

    brand = getattr(user, "brand_profile", None)
    if brand is not None:
        if Payment.objects.filter(campaign__brand=brand).exists():
            brand.company_name = "Anonymiseret virksomhed"
            brand.cvr = ""
            brand.website = ""
            brand.city = None
            brand.save()
            summary.append("brand profile anonymized (payment records kept)")
        else:
            brand.delete()
            summary.append("brand profile deleted")

    EmailAddress.objects.filter(user=user).delete()
    SocialAccount.objects.filter(user=user).delete()

    user.email = f"slettet-{user.pk}@anonymiseret.invalid"
    user.first_name = ""
    user.last_name = ""
    user.is_active = False
    user.set_unusable_password()
    user.save()
    summary.append("user anonymized and deactivated")

    for session in Session.objects.all():
        if session.get_decoded().get("_auth_user_id") == str(user.pk):
            session.delete()

    return "; ".join(summary)


def export_user_data(user: User) -> dict:
    data = {
        "user": {
            "email": user.email,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
            "terms_version": user.terms_version,
        }
    }

    creator = getattr(user, "creator_profile", None)
    if creator is not None:
        data["creator_profile"] = {
            "display_name": creator.display_name,
            "city": creator.city_name,
            "bio": creator.bio,
            "listed": creator.listed,
            "verified": creator.verified,
            "niches": [t.name for t in creator.niches.all()],
            "social_links": [
                {"platform": s.platform, "handle": s.handle, "follower_count": s.follower_count}
                for s in creator.social_links.all()
            ],
            "photos": [p.image.name for p in creator.photos.all()],
            "verification_requests": [
                {"status": v.status, "created_at": v.created_at.isoformat()}
                for v in creator.verification_requests.all()
            ],
            "briefs_received": [
                {
                    "campaign": b.campaign.name,
                    "brand": b.campaign.brand.company_name,
                    "message": b.message,
                    "status": b.status,
                    "created_at": b.created_at.isoformat(),
                }
                for b in creator.briefs.select_related("campaign__brand")
            ],
        }

    brand = getattr(user, "brand_profile", None)
    if brand is not None:
        data["brand_profile"] = {
            "company_name": brand.company_name,
            "cvr": brand.cvr,
            "website": brand.website,
            "city": brand.city_name,
            "campaigns": [
                {
                    "name": c.name,
                    "description": c.description,
                    "tier": c.tier,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                    "payments": [
                        {
                            "mollie_payment_id": p.mollie_payment_id,
                            "amount_ore": p.amount_ore,
                            "status": p.status,
                            "created_at": p.created_at.isoformat(),
                        }
                        for p in c.payments.all()
                    ],
                    "briefs_sent": [
                        {"creator": b.creator.display_name, "message": b.message, "status": b.status}
                        for b in c.briefs.select_related("creator")
                    ],
                }
                for c in brand.campaigns.prefetch_related("payments", "briefs__creator")
            ],
            "shortlists": [
                {"name": s.name, "creators": [e.creator.display_name for e in s.entries.select_related("creator")]}
                for s in brand.shortlists.all()
            ],
        }

    from messaging.models import Message, Review

    data["messages_sent"] = [
        {"deal_id": m.deal_id, "body": m.body, "created_at": m.created_at.isoformat()}
        for m in Message.objects.filter(sender=user)
    ]
    data["reviews_written"] = [
        {"deal_id": r.deal_id, "rating": r.rating, "text": r.text, "created_at": r.created_at.isoformat()}
        for r in Review.objects.filter(author=user)
    ]
    return data
