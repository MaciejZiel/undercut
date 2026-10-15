# ADR 005: Self-hosted home server

Status: accepted

## Decision
Production runs on a self-hosted home server at `undercut.maciejzielinski.dev`: PostgreSQL,
the API, the outbox worker, the scheduler and the Next.js server as plain processes under
restart loops, behind nginx and a Cloudflare Tunnel (no open ports). Docker Compose is used
for local development and CI only.

## Consequences
- No Redis in production: the cache is per process and everything that must be shared
  (sessions, outbox, rate limits that matter) lives in PostgreSQL.
- Deployment is documented in `deploy/termux/` with backup-first, restart-by-port and
  single-reload rules. Backups are logical (`pg_dump`).
