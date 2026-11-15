# Undercut: plan

A public site for F1 fans built on real data since 1950. Flagship portfolio project, non-commercial.
Source of the requirements: the document set `00`–`07` (docx). This plan overrides them where they differ.

> Translated from the Polish original. Decisions and stages are kept as they were planned; the
> status table is the last state recorded in the plan.

## Decisions

| # | Area | Decision |
|---|---|---|
| 1 | Architecture | Modular monolith, event-driven |
| 2 | Events | Transactional outbox in PostgreSQL (Django model `OutboxEvent`) |
| 3 | Worker | Own loop `manage.py run_outbox_worker` (`SKIP LOCKED`), no Celery |
| 4 | Scheduling | Own scheduler that publishes events to the outbox |
| 5 | Modules | `catalog`, `ingestion`, `standings`, `analytics`, `accounts`, `predictions`, `notifications`, `events`. Modules do not import each other's models (`import-linter` in CI) |
| 6 | Events | Thin (identifiers + version), idempotent handlers, at-least-once delivery, ordering per key (for example per session) |
| 7 | Hosting | Home server (Termux, aarch64) behind Cloudflare Tunnel and nginx, at `undercut.maciejzielinski.dev`. No Docker in production: PostgreSQL 18 runs natively, processes run under supervisor loops, Next.js as a Node server. Compose only for development and CI. No Redis and no Caddy. Backups with `pg_dump` to `~/backups/`. Host rules: `~/hosting/RULES.md`, `DEPLOYMENT.md` |
| 7a | Licences | A personal (not company) repository, so `psycopg` (LGPL-3.0) is accepted. Should the project ever become a company project, that needs approval |
| 8 | Time-series data | Plain PostgreSQL tables, index `(session_id, driver_id, ts)`. Partitioning only for `LocationSample`, if it is added |
| 9 | Auth | Django sessions + CSRF, `django-allauth` headless, admin 2FA (`django-otp`) |
| 10 | Name | Undercut (can change at any time) |
| 11 | Repository | New `undercut` repository, everything from scratch. The old `Motorsport_API` stays as an archive |
| 12 | Frontend | Next.js (App Router) + TypeScript, TanStack Query, ECharts, Tailwind, `next-intl` |
| 13 | API types | `drf-spectacular` → `openapi-typescript` + `openapi-fetch` |
| 14 | Rendering | Catalog pages rendered on the server with a cache that events invalidate (Next.js revalidation tags). Charts, replay, predictions and favourites on the client |
| 15 | History import | The Jolpica CSV dump to start, then the API for the difference. Both sources map to the same DTOs |
| 16 | Tests | PostgreSQL everywhere, `pytest` + `factory_boy`, recorded fixtures without network in CI, double-delivery tests for events |
| 17 | Rebuild | Big bang. No working site in the meantime, hence the order below |

Traffic: Caddy routes `/api` and `/admin` to Django and the rest to Next.js. One domain, so no CORS.

## Priorities
- Most important: correctness and quality of the backend, the data, the events and the tests. The UI is done as well as reasonably possible, but polish (fine-tuning, small effects) waits for stage 7.
- Tests are written from the start, but where a bug hurts (outbox, import, standings, scoring, database constraints).

## Stages

| Stage | Contents | What can be shown |
|---|---|---|
| 0. Skeleton | Repository, Compose (PostgreSQL, Django, Next.js, Caddy), CI, modules + `import-linter`, custom `User`, sessions | `docker compose up` works, CI green |
| 1. Events | Outbox, worker, scheduler, idempotency tests | A test event goes through the whole cycle |
| 2. Data | Model v2, Jolpica client, CSV dump import + difference, standings, `SyncRun`, admin panel | All of F1 history in the database, sync after a race weekend |
| 3. Catalog and standings | Driver, constructor, circuit, season, round, standings, dashboard | A version fit for a portfolio |
| **Deployment on DigitalOcean** | Production, TLS, admin 2FA, backups, monitoring | A public link |
| 4. Analytics | OpenF1 client, positions, laps, tyres, pit stops, head-to-head | The strongest argument for an analyst |
| 5. Accounts and predictions | Registration, Google, favourites, predictions, leagues, e-mails | The full user loop |
| 6. Replay | Timeline, controls, optionally a track map and live data | The "wow" effect |
| 7. Polish | Demo account, SEO, accessibility, README with a GIF | Release |

The functional scope (FR and NFR) stays as in the documents, with the corrections from this plan.
An example event chain: `SessionResultsFinalized` → standings, prediction points, e-mails, Next.js cache revalidation.

## Defaults from the documents (unchanged)
- No driver photos and no F1 or team logos (initials on the team colour).
- Paid OpenF1 live data postponed, decision before stage 6.
- Interface in English, `next-intl` from the start.
- Data from Jolpica-F1 and OpenF1 (CC BY-NC-SA 4.0): no monetisation, attribution on the "Sources" page and in the footer.
- Name and logo without "F1" in a form that suggests anything official.

## Status (kept up to date)

| Stage | State |
|---|---|
| 0. Skeleton | done (CI, Compose, modules, import contracts) |
| 1. Events | done (outbox with per-handler delivery, scheduler with job providers) |
| 2. Data | done: history import 1950 to today (30 s) with standings, sync from the API after sessions, corrections, calendar with session times |
| 3. Catalog and standings | done (API and pages), titles, title calculator, comparison, matrix, dashboard; `.ics` calendar in progress on the frontend |
| Deployment | files ready (`deploy/termux/`), **waiting for the owner's approval** |
| 4. Analytics | done: OpenF1 import, API, views; not yet verified on a live weekend |
| 5. Accounts and predictions | done: allauth, favourites, predictions, leagues, e-mail after a race; Google sign-in (ADR 006) done in code, needs keys on the server |
| 6. Replay | done (API and player); track map and live timing deliberately postponed |
| 7. Polish | in progress. Done without UI: SEO, "Sources" and "Privacy" pages, backups and a restore test, E2E in CI, Google sign-in (ADR 006), SMTP (Brevo), HTML e-mails, alert on failed syncs, `resync_round`, weekly check-up e-mail, CSP, type-check gate (pyright, zero errors), 96% coverage with a 90% threshold, dependency audit (osv-scanner, npm audit), dependency-free load test. Left: UI (the "Yours" section, career charts, session banner, circuit card), Lighthouse and accessibility, Tailscale for the admin panel, an off-device backup copy |

Verified on real data: number of world champions, constructors' titles, standings of selected
seasons, the moment the 2024 title was decided, head-to-head records.

## To do before stage 0
- [x] Public repository.
- [x] Domain: no purchase, the subdomain `undercut.maciejzielinski.dev` (A record to the droplet, TLS from Caddy).
- [ ] Check in the Jolpica documentation what the CSV dump looks like and whether it can be downloaded without logging in (when planning stage 2). Fallback: import through the API as a resumable job.

## To rewrite in the documents
- `04`: sync schedule (jobs fetch data, everything else is handlers), the Celery section.
- `05`: stack (Next.js instead of React + Vite, no Celery, sessions), hosting.
- `06`: stages as in the table above.
- `02`: FR-504 and FR-505 (events), FR-801 (idempotency).
