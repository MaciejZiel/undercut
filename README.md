# Undercut

Formula 1 stats, race analytics and a podium prediction game, on real data from 1950 onwards.
Unofficial fan project, not affiliated with Formula One Group or the FIA. Non-commercial: no ads,
no payments.

Live: https://undercut.maciejzielinski.dev (deployment in progress)

## What it does

- **Catalog and history:** every season since 1950, rounds, circuits, drivers, constructors and
  results, with the constructor recorded on race day. Championship tables per round, a points
  progression chart, title statistics.
- **Race analytics (2023 onwards):** lap-by-lap positions, lap times with slow-lap filtering,
  tyre strategy, pit stops with a team ranking, weather and race control messages.
- **Replay:** play a race back from stored data with a timeline, speeds up to 60x and event markers.
- **Accounts and predictions:** registration with e-mail verification, favourites, podium
  predictions locked on the server at qualifying start, automatic scoring, global and private
  league leaderboards, an e-mail after each race (opt-in).
- **Self-updating:** results, standings and corrections are synced after every session by an
  event-driven pipeline; the frontend cache is purged precisely when data changes.

## Architecture in one minute

A Django **modular monolith** (catalog, ingestion, standings, analytics, accounts, predictions,
notifications, webcache) plus a Next.js frontend. Modules never import each other's models:
they call small public interfaces and react to **events** stored in a PostgreSQL **transactional
outbox** (same transaction as the data change, per-handler retries, no broker).
See [docs/architecture.md](docs/architecture.md) and the decisions in [docs/adr](docs/adr).

| Layer | Choice |
|---|---|
| Backend | Django 6, DRF, drf-spectacular (OpenAPI), django-allauth headless (sessions) |
| Frontend | Next.js (App Router), TypeScript, Tailwind, TanStack Query, ECharts |
| Data | PostgreSQL 16 only (unaccent, trigram, JSONB, `SKIP LOCKED`) |
| Quality | pytest + factory_boy on real PostgreSQL, import-linter module contracts, ruff, Vitest, GitHub Actions |

## Run it

```bash
cp .env.example .env
make up            # everything in Docker, http://localhost:8080
```

Development with hot reload (needs `uv` and Node 24):

```bash
make db            # PostgreSQL and Redis only
make backend-dev   # API on :8000
make frontend-dev  # Next.js on :3000
```

Load the real history (about 30 seconds, free Jolpica dump, no account needed):

```bash
cd backend
uv run python manage.py migrate
uv run python manage.py import_history --download
```

Tests (run files or folders one at a time on small machines):

```bash
cd backend && uv run pytest tests/catalog -q
cd frontend && npm test
```

## Data sources and attribution

Results and standings: [Jolpica-F1](https://github.com/jolpica/jolpica-f1) (CC BY-NC-SA 4.0).
Lap, stint, pit stop, position and weather data: [OpenF1](https://openf1.org). Both are
community projects used here for non-commercial purposes; any derived data dump must keep the
same terms. No official logos or driver photos are used.

## Self-hosting

Production runs on a self-hosted home server without Docker: PostgreSQL, gunicorn, the outbox
worker, the scheduler and the Next.js server as plain processes under restart loops, behind
nginx and a Cloudflare Tunnel. Start scripts, an env example, nginx snippets and a
deploy/update/rollback runbook are in [deploy/termux/](deploy/termux/README.md).
`psycopg[c]` replaces `psycopg[binary]` on that platform (handled by `install.sh`).

## Project status

See [docs/PLAN.md](docs/PLAN.md) for the plan, [docs/events.md](docs/events.md) for the event
catalog.
