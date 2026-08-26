# Marketplace (working name undecided)

Swipe-first marketplace connecting Danish SMBs with Danish nano/micro creators
(1k–50k followers). Brands browse and shortlist free, pay per campaign to send
briefs; negotiation is bounded to three proposals; chat opens on acceptance.
Creator compensation runs off-platform in MVP. Product spec:
[docs/founder-poc-brief.md](docs/founder-poc-brief.md).

**Stack:** Django 5 + django-ninja · django-allauth (headless, email-code +
Google) · Mollie (per-campaign one-off payments) · Postgres · Vue 3 + Vite SPA
with Nuxt UI v4, TanStack Vue Query, and Tailwind v4 · Docker Compose.

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

**Seed data**: `docker compose exec backend python manage.py seed_creators
--count 25` fills the deck with fake Danish creators (photos, niches, bios,
follower counts); `--clear` removes them again (they live on `@seed.invalid`
emails).

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

## Operations notes

- **Real Mollie test-mode**: set `MOLLIE_API_KEY=test_...` in `.env` and
  restart. On localhost the webhook URL is omitted (Mollie requires a public
  URL) and the payment-return page's reconcile-on-poll confirms payments
  instead; deployed environments get the webhook automatically via
  `BACKEND_URL`.
- **Waitlist → invites**: admin *Waitlist entries* → select → "Create invite
  codes and email selected" generates a `KVAEK-XXXXXX` code per entry and
  emails it.
- **Verification**: creators upload evidence from their profile; admin
  *Verification requests* → approve/reject actions (approve flips the
  creator's verified badge).
- **GDPR**: verification evidence lives in `backend/private_media/` (never
  web-served; admins view it via an authenticated staff link). Erasure:
  `manage.py erase_user <email>` or the admin action on Users — anonymizes
  and deletes personal data/files while keeping legally required payment
  records. Export: `manage.py export_user_data <email>` prints a full JSON
  dump for portability requests.
- **Terms**: acceptance (timestamp + version) is recorded on the user at
  onboarding; bump `TERMS_VERSION` in `accounts/models.py` when the lawyer's
  final documents replace the drafts in `frontend/src/pages/Terms.vue` /
  `Privacy.vue`.

## Roadmap (post-MVP)

- Weekly digest email (cron/management command)
- Playwright E2E on the critical flows
- Production deployment (EU host, R2/S3 media, Sentry, backups)
- Auto-generated profiles: Instagram/TikTok OAuth (requires registered platform
  apps — start review process once domain + privacy policy exist), stats sync,
  LLM-written bios
- CVR lookup proxy endpoint (frontend currently calls cvrapi.dk directly;
  fails silently if blocked)
- Subscriptions, if introduced: Mollie mandates charged by our own cron —
  not Mollie's Subscriptions API
