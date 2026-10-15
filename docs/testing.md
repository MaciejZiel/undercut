# Testing

| Suite | Where | Runs |
|---|---|---|
| Backend (pytest, real PostgreSQL) | `backend/tests` | CI (`ci.yml`) and locally, one folder at a time |
| Frontend (Vitest, lint, typecheck, build) | `frontend` | CI (`ci.yml`) and locally |
| End to end (Playwright, Chromium) | `e2e` | **GitHub Actions only** (`e2e.yml`) |

## End-to-end tests

They drive the whole stack from `docker-compose.yml` (PostgreSQL, Redis, Django, worker,
scheduler, Next.js, Caddy) through a browser. They are not meant to run on a laptop: the stack
build and Chromium together need several GB of memory.

The workflow `.github/workflows/e2e.yml` runs on pull requests, on pushes to `main` and by hand
(Actions tab, "E2E", "Run workflow"). It:

1. writes a `.env` with random secrets, `DJANGO_DEBUG=true` (so e-mail is printed to the backend
   log) and `HTTP_PORT=8080` (`scripts/e2e/write-env.sh`),
2. builds and starts the stack and waits for `/api/ready/` and the home page,
3. loads data (`scripts/e2e/load-data.sh`): the real history from the Jolpica dump, OpenF1
   analytics for 2024 round 1 only (retried up to three times, the free API rate-limits), and
   `manage.py seed_e2e`,
4. runs the Playwright tests against `http://localhost:8080`,
5. on failure uploads the HTML report and traces (artifact `playwright-report`) and prints the last
   200 log lines of every container.

### What is covered (NFR-504)

| File | Path |
|---|---|
| `01-race-analysis.spec.ts` | dashboard, race page, Analysis view, positions chart rendered, table alternative |
| `02-search-compare.spec.ts` | header search, driver page, Compare with Hamilton, head to head |
| `03-register-favourite.spec.ts` | register in the UI, confirmation link read from the backend log, follow a driver |
| `04-predict-lock.spec.ts` | full pick through the form, qualifying moved into the past, API answers 403 |
| `05-leagues.spec.ts` | create a league, invite code, second user in another browser context joins |
| `06-delete-account.spec.ts` | data export download, delete account, the e-mail can register again |
| `smoke.spec.ts` | main pages answer 200 with one `h1`, the revalidate route refuses callers without the secret |

### Data and helpers

- `seed_e2e` (`backend/apps/ops/management/commands/seed_e2e.py`) gives the last real round of the
  newest season a qualifying session two days ahead and a race after it, so a prediction round is
  open whatever today's date is. It deletes nothing and can be repeated. `--lock` moves the
  qualifying start into the past. The last output line is JSON with the year and round.
- Confirmation e-mails are read with `docker compose logs backend` (`e2e/helpers/mail.ts`), which
  handles quoted-printable soft line breaks and URL-encoded colons.
- The API limits anonymous callers to 60 requests a minute per address and the test browser is one
  address. The tests send the stack's `INTERNAL_API_TOKEN` as `X-Internal-Token`, the same exemption
  the Next.js server uses.
- Every test creates its own users with unique e-mail addresses; the database is not reset between
  tests. Tests run in file order with one worker.

### Reading a failure

Download the `playwright-report` artifact. Traces are recorded on the first retry; open one with
`npx playwright show-trace trace.zip` or at trace.playwright.dev.
