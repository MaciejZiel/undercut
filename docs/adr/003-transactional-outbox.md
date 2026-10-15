# ADR 003: Event-driven modules with a transactional outbox

Status: accepted

## Context
After a race, several things must happen in order: store results, update standings, score
predictions, refresh cached pages, send e-mails. Sources are free volunteer-run APIs and SMTP,
so failures are normal. Direct calls between modules would couple them and make a failure in
one consumer cancel or silently skip the others.

## Decision
Modules publish **thin events** (identifiers and a version) into an `OutboxEvent` table in the
same database transaction as the change. A worker claims due rows with `SELECT ... FOR UPDATE
SKIP LOCKED`, runs the subscribed handlers, and retries failures with exponential backoff
(`dead` after 8 attempts). Delivery is tracked per handler. A small scheduler turns time into
events (daily jobs and data-dependent jobs such as "results due one hour after a session").
No broker, no Celery: the outbox is itself the durable queue.

## Consequences
- At-least-once delivery: every handler is idempotent.
- Ordering is guaranteed per `key` only (for example per session).
- Moving to a real broker later only replaces the transport; handlers do not change.
- Modules cannot import each other's models (enforced by `import-linter`).
