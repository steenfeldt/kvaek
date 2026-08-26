# Marketplace (working name undecided)

Swipe-first marketplace connecting Danish SMBs with Danish nano/micro creators
(1k–50k followers). Brands browse and shortlist free, pay per campaign to send
briefs; negotiation is bounded to three proposals; chat opens on acceptance.
Creator compensation runs off-platform in MVP. Product spec:
[docs/founder-poc-brief.md](docs/founder-poc-brief.md).

**Stack:** Django 5 + django-ninja · django-allauth (headless, email-code +
Google) · Mollie (per-campaign one-off payments) · Postgres · Vue 3 + Vite +
Tailwind SPA · Docker Compose.

## Run

```bash
cp .env.example .env   # defaults are fine for dev
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

- Frontend: http://localhost:5173 (proxies `/api` and `/_allauth` to the backend)
- API docs: http://localhost:8000/api/docs
- Django admin: http://localhost:8000/admin
- Mailpit (login codes, all outgoing email): http://localhost:8025

Creator signup requires an invite code — create one in admin under
*Accounts → Invite codes*. Creators appear in the brand deck only once `listed`
is ticked on their profile (admin, after moderation).

With `MOLLIE_API_KEY` empty (dev), campaign checkout simulates an instant paid
payment and activates the campaign, so the full flow is testable offline.

## Tests

```bash
docker compose exec backend pytest
```

## Architecture rules

- **All state transitions live in `services.py`** (campaigns, billing) — API
  handlers validate/authorize and delegate; nothing else mutates campaign,
  brief, proposal, deal, or payment state.
- **Money is integer øre** everywhere in the backend; format in the frontend.
- **Payment truth comes from Mollie**: webhook and return-page both call
  `reconcile_payment`, which fetches from Mollie's API — request bodies are
  never trusted. `activate_campaign` is idempotent.
- **Anti-circumvention at the API layer**: deck/shortlist responses never
  include creator handles or external links — platform + follower count only.
- **Creator-side silence**: creators only ever see aggregate shortlist counts,
  never which brands saved them.

## Roadmap (post-MVP)

- Campaign/brief/negotiation UI in the frontend (API is done; pages pending)
- Photo upload with server-side resize (Pillow) — model exists
- Transactional emails on brief/proposal/deal events + weekly digest (cron)
- Auto-generated profiles: Instagram/TikTok OAuth (requires registered platform
  apps — start review process once domain + privacy policy exist), stats sync,
  LLM-written bios
- CVR lookup proxy endpoint (frontend currently calls cvrapi.dk directly;
  fails silently if blocked)
- Subscriptions, if introduced: Mollie mandates charged by our own cron —
  not Mollie's Subscriptions API
