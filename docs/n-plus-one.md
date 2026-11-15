# Hunting N+1 queries with pytest-queryguard

The API already had about 30 tests that assert a constant number of queries per endpoint. What
nothing checked was the code that runs *outside* a request: the outbox handlers, the scheduler,
the nightly demo reset and the importers. This page is how that was closed.

## Setup

[pytest-queryguard](https://maciejziel.github.io/pytest-queryguard/) is a pytest plugin that
records the SQL of every test body and reports two kinds of problems for Django:

- **relationship-load**: a foreign key or reverse relation loaded lazily, once per parent row
  (the classic N+1);
- **repeated-statement**: the same statement, with different parameters, run many times in one
  test (a lookup inside a loop).

It needs no settings change: `uv add --dev "pytest-queryguard[django]"`, and every test is
checked. The first run used `--queryguard-mode=warn --queryguard-json=queryguard.json` in CI to
get the full list without failing the build (the backend tests need PostgreSQL, which runs in
GitHub Actions).

## What it found

932 tests, 56 with findings, about 40 distinct places. Grouped:

| Finding | Where | Verdict |
|---|---|---|
| no relationship-load in application code | API views and selectors | the existing query-count tests and `select_related`/`prefetch_related` already held |
| race outcome queried once per bot pick (up to 30 times) | demo reset | **fixed**: outcomes for all sample rounds in one call, reused for every pick |
| two user lookups per bot, `get_or_create` per league member | demo reset | **fixed**: one query for existing bots, one for taken display names, one bulk insert of missing members |
| `add_favorite` (5 queries) per demo favourite | demo reset | **fixed**: one `in_bulk` per kind and one bulk insert |
| circuit looked up by slug once per circuit | GeoJSON outline import | **fixed**: one `slug__in` query (13 statements to 1 when nothing needs drawing) |
| lazy `session.round.season` twice per call | a test helper | **fixed**: one `EXISTS` |
| per-entity upserts (`_sync`, `_ids`, `_create_with_slug`, ...) | Jolpica import | accepted: idempotent upserts, bounded by one round, the whole history imports in about 30 s |
| per-recipient checks in the post-race e-mail | notifications | accepted: each recipient gets its own transaction on purpose, that is what makes the e-mail exactly-once on top of at-least-once delivery; SMTP dominates the cost |
| driver matching once per imported session | OpenF1 import | accepted: two queries per session |
| a service called in a loop by the test itself | five tests (arrange steps, worker driven once per attempt) | not application code: `@pytest.mark.queryguard_ignore(kind="repeated-statement")` with the reason next to it |

Effect on the demo reset, measured by the same JSON report: a test that runs one reset went from
**130 SQL statements to 60**, the outbox-driven reset test from 199 to 77, and the number no longer
grows with the number of bots or sample rounds.

## The gate

The suite now runs with queryguard in its default *fail* mode. Every accepted exception is a line
in `backend/pyproject.toml` (`queryguard_ignore`) scoped to one file and function, with the reason
in a comment above it, so a new loop elsewhere, or a new lazy load in an API view, fails CI. Each
CI run uploads `queryguard.json` (statements, database time and findings per test) as an artifact.

## Lessons

- Query-count assertions on endpoints catch regressions you already thought about; a detector
  catches the ones you did not, which here were all in background jobs.
- Not every finding is a bug. Two of the biggest groups were deliberate (exactly-once e-mail,
  idempotent import upserts). Writing the reason next to the ignore rule is the useful part.
- The cheapest fixes were "hoist the read out of the loop": the same outcome, pool or row was read
  for every iteration although it depended only on the round.
