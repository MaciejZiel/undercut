# Operations

Day-to-day running of the self-hosted production server (ADR 005). Install and update steps live in
`deploy/termux/README.md`; this page is about checking, reading, backing up and restoring.
Commands marked [PRODUCTION] change or read the live server and need the owner's approval.
On the server, load the env first: `set -a; . ~/.config/undercut/env; set +a` and run from `~/undercut/backend`
(`.venv/bin/python manage.py ...`).

## Health checks

| Check | Command | Meaning |
|---|---|---|
| Liveness | `curl -s http://127.0.0.1:8110/api/health/` | the API process answers and the database responds to `SELECT 1`. Cheap, use for restart loops |
| Readiness | `curl -s http://127.0.0.1:8110/api/ready/` | 200 only if the database answers, all migrations are applied and the outbox is healthy (no dead events, nothing pending for more than 30 min). 503 lists which check failed |
| Status summary | `GET /api/v1/ops/status/` as a logged-in staff user | outbox counts and oldest pending age, last run per sync job, scheduler and worker heartbeats, latest finished race and when its results were finalized, largest tables |
| Pipeline check | `sh deploy/termux/check-pipeline.sh` | exit 0 and `OK`, or exit 1 with one `PROBLEM <code>: ...` line per issue |

`/api/ready/` is public and reports only pass or fail. The status endpoint needs `is_staff`; because `/admin/` is not
reachable from the internet, read it on the server with the checks above, or `manage.py shell`:
`from apps.ops.status import full_status`.

## check_pipeline and its alerts

`manage.py check_pipeline [--json]` exits 1 when any of these is true. The cron wrapper writes one line per run to
`~/services/logs/undercut-check.log` (`rc=0` is fine).

| Code | Trigger | What it means, what to do |
|---|---|---|
| `outbox_dead` | at least one outbox event has status `dead` (8 failed attempts) | a handler keeps failing. Read `last_error` in the admin or `OutboxEvent.objects.filter(status="dead")`, fix the cause, then set the event back to `pending` with `attempts=0` |
| `outbox_stuck` | oldest pending event is older than 30 minutes | the worker is not draining: it is stopped, crashed in a loop, or events are in long backoff. Check `undercut-worker.log` and the `outbox-worker` heartbeat |
| `heartbeat_stale` | scheduler or outbox worker last reported more than 5 minutes ago | the process is hung or its supervisor stopped. Look at the log, restart that process by PID (see the update checklist) |
| `heartbeat_missing` | a process never reported | never started since the migration (new deploy) or the migration was not applied. Check the supervisors |
| `sync_failing` | the latest run of a sync job failed, and so did the one before it, within the last 24 h | an upstream (Jolpica, OpenF1) or the network is failing. Look at `SyncRun.errors` for the job. The same condition e-mails `ALERT_EMAIL_TO` once at the second failure and then every tenth. After fixing it, `manage.py resync_round <year> <round>` queues a fresh sync (also in the admin: SyncRun list, "Rerun a round") |
| `results_missing` | the latest race ended more than 24 h ago and is not `results_final` | the results sync did not finalize it. Check the `jolpica-api` SyncRun in the status summary and the worker log; the Monday corrections job will not fix a missing race |

The heartbeat is written by `run_scheduler` and `run_outbox_worker` (at most once every 30 s) into the `ops_heartbeat`
table, one row per process.

## Logs

Each supervisor appends stdout and stderr to `~/services/logs/undercut-<backend|worker|scheduler|frontend>.log`.
With `DJANGO_DEBUG=false` the Django processes write JSON lines:

```json
{"ts": "2026-10-15T13:15:00.432+00:00", "level": "INFO", "logger": "undercut.request", "message": "GET /api/v1/seasons/ 200", "request_id": "9f1c...", "method": "GET", "path": "/api/v1/seasons/", "status": 200, "duration_ms": 12.4}
```

- Every API response carries `X-Request-ID`; nginx supplies one, or send your own (8 to 64 characters of
  `A-Za-z0-9._-`). Find everything about one request with `grep <id> ~/services/logs/undercut-backend.log`.
- Errors: `grep '"level": "ERROR"' ~/services/logs/undercut-*.log | tail`. Tracebacks are in the `exception` field.
- Paths are logged as route patterns (`.../unsubscribe/<str:token>/`), never with query strings. A redaction filter masks
  e-mail addresses, passwords, tokens, cookies, bearer headers and credentials in connection URLs, in messages and
  tracebacks. Do not log raw request bodies.
- `/api/health/` and `/api/ready/` are not logged. `LOG_LEVEL` (default INFO) and `LOG_FORMAT=text` change the output.
- The supervisor logs grow without limit; trim them when disk is short (`: > file` on a log you have already read).

## Error reporting (optional)

Set `SENTRY_DSN` in the env file to enable Sentry. The `sentry-sdk` package is deliberately not a project dependency: it
requires `certifi` (MPL-2.0), and new copyleft code needs written approval from Company Management first. After approval
install it into the venv (`backend/.venv/bin/python -m pip install sentry-sdk==<pinned version>`) and record it in
`3rdparty_licenses.md`. Without the package the app logs one warning and runs normally. Settings: no personal data
(`send_default_pii=False`), no request bodies, no local variables, tracing off (`SENTRY_TRACES_SAMPLE_RATE=0`), and every
event passes through the same redaction as the logs.

## Backups

Logical dumps with `deploy/termux/backup.sh`, scheduled nightly by cron (cron lines in the deploy README).

- Output: `~/backups/undercut-<UTC timestamp>.dump` (custom format, mode 600, directory mode 700).
- Retention: newest dump of each of the last 7 days plus newest of each of the last 4 ISO weeks (at most 11 files).
  Only files matching `undercut-YYYYMMDDTHHMMSSZ.dump` are ever deleted.
- It refuses to run when less than 2048 MB is free (`UNDERCUT_BACKUP_MIN_FREE_MB`) and exits with code 2; the dump is
  verified with `pg_restore --list` before it replaces anything.
- Manual run [PRODUCTION]: `sh ~/undercut/deploy/termux/backup.sh`. Also copy the newest dump off the device now and then;
  a backup on the same phone does not survive losing the phone.

## Restore

Test (NFR-602, on request only) [PRODUCTION]: `sh ~/undercut/deploy/termux/restore-test.sh [dump]`. It restores into
`undercut_restore_test`, prints counts for `django_migrations`, `accounts_user`, `catalog_*`, outbox and sync tables,
drops the scratch database and prints `RESTORE TEST PASSED` or `FAILED`. It refuses to start if that scratch database
already exists and never touches `undercut`.

Real restore [PRODUCTION], with the owner's approval:

1. Stop the API, worker and scheduler by PID or port (update checklist, step 7). The supervisors restart them after 5 s,
   so stop the supervisor loops first or do steps 2 and 3 quickly.
2. `pg_restore --clean --if-exists --no-owner -d undercut ~/backups/undercut-<timestamp>.dump`
3. Start the processes again; migrations run on backend start. Run `check_pipeline.sh` and `/api/ready/`.

Restore test log (fill in after each run):

| Date | Dump | Result | Duration |
|---|---|---|---|
| 2026-10-15 | `undercut-20261015T134503Z.dump` (904 KB) | PASSED (77 seasons, 881 drivers, 28,711 results) | 1 s |

## Rotating secrets

All secrets live in `~/.config/undercut/env` (mode 600). Edit it on the server, never paste its contents anywhere, then
restart the affected processes by PID.

| Secret | Effect of rotating | Restart |
|---|---|---|
| `DJANGO_SECRET_KEY` | signs sessions, password reset and unsubscribe links: all users are logged out and old links stop working | API, worker, scheduler |
| `DATABASE_URL` password | change it in PostgreSQL first (`ALTER ROLE undercut PASSWORD ...` via `psql -d postgres`), then in the env file | API, worker, scheduler |
| `REVALIDATE_SECRET` | must be identical for the backend and the Next.js server | worker and frontend together |
| `EMAIL_HOST_PASSWORD` | outgoing mail | worker |
| `SENTRY_DSN` | error reporting | all Django processes |

Generate values with `python -c 'import secrets; print(secrets.token_urlsafe(50))'`. After a restart verify with the
health checks above.

## Deploy and rollback

Follow `deploy/termux/README.md`: "Update checklist" (back up first, `git pull --ff-only`, restart by PID or port, never
`pgrep -f`/`pkill -f`) and "Rollback" (previous commit, restore frontend and nginx copies, database restore only if a
migration must be undone). After every deploy run `manage.py check --deploy` once; the remaining warnings
`security.W005`, `W008` and `W021` are deliberate and silenced in settings.

## Security notes

- Production needs `DJANGO_DEBUG=false`, a real `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
  `DJANGO_CSRF_TRUSTED_ORIGINS`; `check --deploy` flags a missing one (`ops.W001` to `W003`).
- TLS ends at Cloudflare. Django trusts `X-Forwarded-Proto` from nginx (gunicorn listens on loopback only), cookies are
  secure, HSTS is on without subdomains, there is no HTTP-to-HTTPS redirect in Django.
- `/admin/` and `/_internal/` are not reachable through the tunnel; the nginx gate is explained in
  `deploy/termux/nginx-server.conf`. `/api/v1/ops/status/` is open to staff sessions only.

## Load test (NFR-101..103)

`scripts/perf/load_test.py` (standard library only; k6 is AGPL-3.0 and is not used) sends GET requests from several
threads and prints p50/p95/p99 latency and the error rate. It exits 1 above `--p95-ms` (default 500) or above
`--max-errors` (default 1 %).

```
INTERNAL_API_TOKEN=... python scripts/perf/load_test.py https://undercut.maciejzielinski.dev \
    /api/v1/seasons/ /api/v1/drivers/ /seasons/2024 --connections 10 --seconds 30
```

Run it against your own deployment only, and keep the load modest on the home server. Without `INTERNAL_API_TOKEN` the
anonymous throttle (60 requests per minute per address) answers 429, which counts as errors.

## Catalog data commands (OpenF1)

| Command | What it does |
|---|---|
| `import_practice [--since 2023] [--all]` | practice results (FP1 to FP3) for sessions that have none, from OpenF1 `session_result`. The scheduler does the same hourly after each practice session |
| `import_circuit_outlines [--year Y] [--force]` | draws the track outline of every circuit raced since 2023 from one lap of the race winner (3 requests per circuit). Done automatically after a race's analytics import |
| `resync_round <year> <round>` | queues a fresh results, practice and analytics sync of one round |

The circuit page derives the lap record (fastest race lap on record, Jolpica data from 2004) and, until a real length
is entered, an estimated length measured on the outline (rounded to 100 m, flagged `length_is_estimate`).
