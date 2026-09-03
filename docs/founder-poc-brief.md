MARKETPLACE MVP
WORKING NAME UNDECIDED
AUG 2026
A Danish influencer
marketplace, at the point where the engineering is done and the launch is legal.
A swipe-first web platform for Danish SMBs and nano/micro creators. Built to prove one thesis: that a fair, local, per-campaign product beats an English-first agency SaaS in this segment.
PREPARED AS
Principal Architect + PM
STATUS
Private-beta-ready
CODEBASE
elsborgjorgensen/influencer-marketplace
DEPLOYED
Vercel · Supabase EU · Mollie test
CONTENTS
i
Executive Summary
ii
Business Goals & Key Decisions
iii
System Architecture & Tech Stack
iv
Trade-offs & Rationale
v
Future Constraints & Risks
i
EXECUTIVE SUMMARY
What it is, and where it stands.

A swipe-first, mobile-first web marketplace connecting Danish small businesses with Danish nano and micro content creators (1k–50k followers). Brands discover creators visually, save them privately to shortlists, pay a per-campaign fee to unlock brief sending, negotiate proposals under a bounded state machine, close deals, and coordinate delivery via in-app chat.

Money moves in two places: the platform's tier fee runs through Mollie (currently test-mode); the creator's own compensation for the work runs off-platform between the two parties. This is deliberate MVP scope, not a limitation to fix later.

WHERE THE BUILD STANDS

All of Phases 0–3a shipped over roughly twelve development sessions. The full monetized round-trip works end-to-end on production: brand signs up, creator profiles populate the pool, brand swipes, shortlists, creates a campaign, pays via Mollie, sends briefs, creator responds, proposal exchange alternates until accepted or declined, deal auto-created on acceptance, chat opens with contact details, both mark completion, both leave reviews. Verified-badge flow, admin panel, moderation queues, and rendered weekly digests all functional.

THE ONE HONEST SENTENCE
The engineering is at "ready for private beta today." What sits between here and a public launch is legal drafting, brand identity, and cold-start seeding — not code.
WHAT'S STILL MISSING

Phase 3b (last engineering piece). Transactional emails via Resend on the key events (brief received, proposal received, deal made) and scheduled weekly digest sending via cron. Replaces the currently preview-only digest rendering.
Business & legal. A product name and .dk domain, Danish ApS incorporation, and a marketplace-competent Danish lawyer drafting GDPR-compliant terms and privacy policy. Budget roughly 5–15.000 kr and two to four weeks.
Cold-start seeding. First 40–60 Danish creators onboarded from personal network before any brand sees the pool. Then first three to ten SMB pilots in one city.
ROUGH ECONOMICS

Working assumption: about 1.600 kr per brand per year in gross revenue at two campaigns per year at an average Standard tier. Break-even on infrastructure is around fifty paying brands per month. A meaningful business needs several hundred.
ii
BUSINESS GOALS
The decisions that define the product.

Every product is a bet. These are the bets that determined every code decision downstream. Each is deliberate. Each is worth re-litigating later — but only after data.

THE WEDGE

Existing platforms — Aspire, Grin, Modash — are US/UK-centric, English-first, and priced at $500–$2,000/month. A Danish-first, per-campaign product with local payment methods (MobilePay, Dankort) and creators the buyer's audience actually recognizes is a real gap. The founder's existing personal network among Danish creators solves the classic supply-side cold-start problem.

SEGMENTS (MVP SCOPE)

SIDE    SEGMENT    WHY THIS SEGMENT
Brand
Danish SMBs — cafés, boutiques, small e-commerce, local services. Buyer is the owner.    Underserved. Too small for agencies, too intimidated by existing platforms. Willing to pay under 1.000 kr for a first campaign to try.
Creator
Danish nano/micro on Instagram and TikTok (1k–50k followers).    Match the buyer's budget. Higher engagement than macros. Founder already has direct contacts here — supply side is not the cold-start problem.
BUSINESS MODEL — LOCKED IN

Pay-per-campaign, no subscription. SMB mental model is "I spent X on this campaign." Subscriptions in this segment create anxiety and churn. Three tiers, DKK excl. VAT:

Starter
299 kr
5 briefs · first-time users
Standard
799 kr
20 briefs · typical SMB campaign
Reach
1.999 kr
60 briefs · seasonal push
Creators pay nothing. No listing fee, no commission in MVP. The platform monetises only the brand side. In-platform payments with roughly ten percent commission is the primary v2 monetisation lever — it becomes accessible once the parties trust the flow.

PRODUCT PRIMITIVES

Silent shortlisting. Brands save creators privately. Creators only see aggregate counters — "3 brands saved you this week" — never identities. Protects the creator inbox; preserves the "brands must pay to reach out" incentive.
Open negotiation. The creator opens with a price, then the sides alternate counter-proposals with no cap on rounds; a negotiation ends only when one side accepts or declines. (Originally bounded to three proposals; the cap was dropped in September 2026 because it forced an accept-or-decline when both parties were close.)
Chat opens only after acceptance. No pre-brief messaging, ever. Two reasons that both matter: creators don't get spammed, and the "pay to send a brief" pricing wouldn't survive free DMs.
ANTI-CIRCUMVENTION
Twelve-month non-circumvention clause in ToS: after being matched, parties can't work together off-platform. Bypass fee 4.999 kr ex VAT per violation. Detection is passive — internal signals from the platform's own data, not web crawlers. Crawlers are wrong for MVP: false-positive dominated, GDPR-exposed, and poor ROI. The real long-term lever is offering in-platform payments as a service in v2 — invoicing, receipts, VAT handling — that people want to use.
"Two decisions worth re-litigating later: no commission model in MVP (real revenue lives on take-rate, not tier fees), and manually approved verified badges (fine for hundreds, not thousands)."
iii
ARCHITECTURE
The stack, in one page.

Everything is EU-hosted for GDPR. Everything on free tiers at MVP scale. Nothing custom where an off-the-shelf tool is acceptable.

LAYER    CHOICE    WHY
App framework
Next.js 16.3 (App Router, Turbopack, React 19.2)    Server Components for data, Client for interactivity. Vercel-native. Talent pool is deep for future hiring.
Language
TypeScript strict + noUncheckedIndexedAccess    Catches a whole class of runtime bugs at build. Free correctness.
UI system
Tailwind CSS v4 · shadcn/ui (Base UI primitives)    Component code lives in the repo. No black-box library. Warm terracotta design system.
Data
Supabase Postgres · 20+ tables · per-table RLS · security-definer RPCs    Authorisation at the DB layer, not just app boundaries. Every new endpoint gets a WITH CHECK clause, not a per-endpoint hope.
Auth
Supabase Auth · email magic link + Google OAuth    Zero custom auth code. Post-login routing is a single pure function.
Storage
Supabase Storage · 3 buckets with per-user folder RLS    Photos public. Verification evidence private (admin signed URLs). Uploads go through service-role because @supabase/ssr doesn't propagate the user JWT to storage — a known quirk we route around.
Realtime
Supabase Realtime · postgres_changes + broadcast fallback    Postgres-changes broadcasts are fragile under RLS with joins. Server-side broadcast on the same channel is the reliable path; postgres_changes is belt-and-suspenders.
Payments
Mollie · hosted Checkout · webhook + return-page polling    EU-native. Native MobilePay + Dankort. Lower fees on Danish payment methods. Amounts stored as integer øre — no float precision issues.
Observability
Sentry (EU) · PostHog (EU)    Errors + product analytics + session replay, GDPR-hosted.
Email
Resend (installed, wiring in Phase 3b)    Transactional templates in Danish + weekly digest sending.
Deploy
Vercel Hobby (Frankfurt) · Supabase Cloud (Frankfurt) · GitHub Actions CI    Auto-deploy on push. Typecheck + lint + build gate every merge.
i18n
next-intl v4 · da default · en toggle    Danish-first UX matters commercially. English toggle signals eventual Nordic expansion.
THE DATA MODEL IN FIVE SENTENCES

Identity — app_users, creator_profiles, brand_profiles, plus social accounts, photos, niche tags, and verification requests.
Discovery — shortlists and their entries, swipe events with a 30-day seen-gate, and debounced profile views (six-hour cooldown per brand/creator pair).
Monetisation — campaigns, briefs, proposals, deals, payments (Mollie-backed; øre integers).
Post-deal — reviews (one per party per deal) and messages (chat, denormalized parties for Realtime RLS).
Moderation — reports queue, handled from the admin panel.
RUNTIME PATTERNS WORTH NAMING

Single post-login router. One pure function decides where any user lands after auth. Prevents drift.
Server actions + service-role admin client. Session-aware client verifies identity, then service-role client does the write that RLS would over-complicate. Identity check runs before the service-role call — service-role is a controlled backdoor, not a security hole.
Idempotent campaign activation. Called by both the payment webhook and the return page. Safe to call twice — only flips draft → active once.
Denormalized chat parties. brand_id and creator_id on messages so RLS is a plain column check. Trigger keeps them in sync. Fixes an otherwise-silent Realtime bug.
Money as integer øre. No floats. Divide by 100 in the view layer.
iv
TRADE-OFFS
Every choice was a trade.

Next.js 16 (Turbopack) over Remix / Astro / plain Node.
Best-in-class Vercel deploy story and the widest talent pool for future hiring. Cost paid: Next 16 is bleeding-edge — the middleware.ts to proxy.ts rename, React Compiler's set-state-in-effect lint rule, and async params/searchParams all bit us mid-build. Payoff: Server Components make data-fetching feel like normal server code with none of the API-plumbing tax. Would pick it again.

Supabase over a hand-rolled backend or Firebase.
Postgres, RLS, Auth, Storage, and Realtime in one product, on a free tier that covers MVP. Trade-off: Supabase is opinionated and Realtime + RLS has real edge cases (see chat). The alternative — Node, Postgres, custom auth, Redis pubsub, S3 — is three times the code and six months slower to first users. RLS pays off later: every new endpoint gets its authorisation from a WITH CHECK clause, not from a per-endpoint check that someone will forget.

Mollie over Stripe.
Danish-market fit: native MobilePay and Dankort, EU-native (no data-transfer complications), lower fees on Danish methods. Trade-off: Mollie's dev UX is a step behind Stripe, and there's no equivalent to Stripe Connect for future in-platform payments — that's a bigger project when we get there. Acceptable because conversion matters more than dev ergonomics in this market.

Mobile-first web (PWA-ready), not native app.
Zero App Store friction, one codebase, deploy in seconds. Trade-off: no true push notifications, no home-screen presence, no in-app purchase (though DKK means we'd want Mollie anyway). Nano/micro creators and SMB owners live in a browser; native app friction isn't justified until proof of demand.

Client-side image compression, not server processing.
Photos go from 3–8 MB down to about 200 KB before upload. Saves Supabase Storage bandwidth. Cost: relies on user's device having a modern browser — fine for any phone camera younger than a decade.

Admin client for related reads, session client for writes.
Every time a page relied on Supabase's nested !inner join through an RLS-controlled table, it broke silently — shortlist detail, creator deals, brand deals. Consistent pattern now: session client verifies the caller owns the parent, then service-role client fetches the related rows. Service-role isn't a backdoor; it's a controlled bypass with the identity check enforced by the app layer, before it runs.

Denormalized chat parties on messages.
Solves a real Supabase Realtime pitfall: complex EXISTS-with-joins in a SELECT policy aren't evaluated correctly by the Realtime replication service, so cross-user updates silently don't push. Two extra columns per message, kept synced by a BEFORE INSERT trigger, backfilled once. Small cost, essential UX win.

Warm terracotta committed as CSS variables.
Distinctive over "SaaS blue"; warm cream over pure white. Marketplace is about people — the palette leans editorial. Trade-off: hand-crafted design system without a design tool; iteration requires code changes. Right for a founder-led product where taste is coherent and the surface is small.

THE PATTERN TO REMEMBER
Three separate class of bugs — nested RLS inner-joins, storage JWT propagation, Realtime RLS with joins — all had the same shape: Supabase's higher-level abstractions have edge cases where RLS silently produces empty or unpushed results. The workaround is always the same: session client for auth, admin client for the actual read/write after identity is verified. Formalising this as a helper is a good early v2 refactor.
v
CONSTRAINTS & RISKS
What breaks first, and how loud.

Risks below are tagged by class. Technical risks are cheap to fix and mostly known. Product risks show up after real users. Business risks decide whether the whole thing works. Ops risks are the ones you don't notice until you need them.

TECHNICAL
Supabase Free tier limits.
500 MB DB, 1 GB storage, 50k MAU. Real traffic pushes to Pro at $25/mo fast. Not a blocker, just budget it.
TECHNICAL
Vercel Hobby has no cron.
Phase 3b's weekly digest needs Vercel Pro ($20/mo), Supabase pg_cron, or GitHub Actions on a schedule. Pick one when we get there.
TECHNICAL
Realtime + RLS is fragile.
Two failure classes patched. Any new realtime feature needs a simple RLS check on the streamed table — denormalize early.
TECHNICAL
No automated tests.
CI runs typecheck + lint + build only. Highest-value pre-launch investment: Playwright E2E on the five critical flows — auth, campaign pay, brief send, proposal exchange, deal complete.
TECHNICAL
Migrations are pasted, not pushed.
Fine for solo dev. Needs Supabase CLI + supabase db push before team scale.
PRODUCT
Design is minimally viable, not delightful.
One design pass shipped. Empty states, loading states, error messages functional but not crafted. Budget one more polish pass before broad launch.
PRODUCT
No accessibility audit.
Semantic HTML mostly there via shadcn. Nothing tested with screen readers. WCAG AA pass on the five critical flows before public launch.
PRODUCT
No search / no browsing beyond swipe.
By design. First time a brand says "I want to find that creator I saw last week", the pain is real. Add plain search-by-name later.
BUSINESS
Cold start is the real risk.
Marketplaces die on the supply side. Seed 40–60 creators personally before any brand sees an empty page. Founder has direct contacts — this is a solvable problem.
BUSINESS
Willingness to pay is unproven.
Tier pricing is a hypothesis. Validate with 5–10 SMB conversations before public launch. Adjust — don't guess.
BUSINESS
Retention hypothesis unproven.
Two campaigns per year per brand assumes brands come back after first success. If they don't, unit economics implode. Track first-90-days retention obsessively.
BUSINESS
Legal exposure without a lawyer.
GDPR, Danish Marketing Practices Act on sponsored content disclosure, tax handling for creator payments — non-negotiable before public launch. Budget 5–15.000 kr and two to four weeks.
BUSINESS
Payment processor risk.
Mollie is test-mode. Live-mode requires KYC — days to weeks. Start before you need it.
OPS
Founder is a single point of failure.
All admin access, all secrets, all decisions in one person. Before public launch: shared password manager with a trusted second, runbooks for "site down", "Mollie failing", "creator reports harassment".
OPS
No incident alerting.
Sentry + PostHog exist; alerting on threshold breaches doesn't. Wire at least one Sentry alert to email on error spikes.
OPS
Backups.
Supabase Free has no automatic backups. Enable Pro before real user data lives here, or take manual pg_dump weekly.
OPS
GDPR data-export / deletion.
No user-facing "delete my account" or "download my data" yet. Right of erasure is a GDPR requirement. Add before public launch; manual admin process is fine to start.
OPS
Domain, name, entity.
Undecided. Publicly launching without a coherent brand identity leaves money on the table. Business track (name → domain → ApS → lawyer) can run in parallel to Phase 3b engineering. Starting soon compresses time-to-launch.
"The engineering is at 'ready for private beta today.' The next three to six weeks of calendar time is more about business work than about code."
Prepared for internal use. Not for distribution.
Aug 2026 · v0.1