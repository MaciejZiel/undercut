# Undercut

Formula 1 stats, race analytics and predictions on real data from 1950 onwards.
Unofficial fan project, not affiliated with Formula One Group or the FIA.

Status: early development. See [docs/PLAN.md](docs/PLAN.md) for the architecture decisions and stages.

## Stack

- Backend: Django + DRF, modular monolith, event-driven (transactional outbox in PostgreSQL)
- Frontend: Next.js (App Router), TypeScript, Tailwind
- Data: PostgreSQL 16, Redis (cache)
- Edge: Caddy (one origin for frontend and API)

## Run it

```bash
cp .env.example .env
make up            # http://localhost:8080
```

Local development with hot reload:

```bash
make db
make backend-dev   # :8000
make frontend-dev  # :3000
make test
```

## Data sources

Jolpica-F1 and OpenF1 (both CC BY-NC-SA 4.0, non-commercial use, attribution required).
