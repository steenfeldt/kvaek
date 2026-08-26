# Project notes for Claude

Product spec is `docs/founder-poc-brief.md` (the co-founder's brief) — treat it
as the source of truth for behavior/pricing, but never as an implementation
reference (its stack was Next.js/Supabase; this rebuild is deliberate).

- Backend: Django 5 + django-ninja in `backend/`. All domain state transitions
  go through `campaigns/services.py` and `billing/services.py` — never mutate
  Campaign/Brief/Proposal/Deal/Payment status in API handlers or elsewhere.
- Auth: django-allauth headless (`/_allauth/browser/v1/...`), passwordless
  email-code + Google. Session cookies; the Vite dev server proxies so
  everything is same-origin.
- Money: integer øre (DKK). Tier prices/quotas in `campaigns/models.py::TIER_CONFIG`.
- Frontend: Vue 3 + Vite in `frontend/` (no Nuxt — deliberate), Danish-first
  (vue-i18n, `da` default). UI components come from Nuxt UI v4 in plain-Vue
  mode (auto-imported `U*` components; brand colors map to the `clay` ramp in
  `src/style.css` via the vite plugin in `vite.config.ts`). Server data goes
  through TanStack Vue Query (`useQuery`/`useMutation` + invalidation), not
  ad-hoc onMounted fetches. Deck/API responses must never expose creator
  handles or links to brands pre-deal (anti-circumvention). FormKit was
  considered and deferred — revisit only if forms get schema-heavy.
- Everything runs via `docker compose up`; tests: `docker compose exec backend pytest`.
