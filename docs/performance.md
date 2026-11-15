# Performance

Load-test numbers from GitHub Actions, measured by the [`Perf`](../.github/workflows/perf.yml)
workflow. They come from a disposable stack on a CI runner, never from the production server.

## Method

- **Stack:** the full `docker compose` setup (Caddy, Next.js server, Django under gunicorn with 3
  workers, PostgreSQL 16, Redis) built from the commit, with `DJANGO_DEBUG=false` as in production.
- **Data:** the complete 1950-2025 history from the Jolpica dump and OpenF1 analytics for one race
  (2024 Bahrain, round 1), loaded by `scripts/e2e/load-data.sh`.
- **Load:** [`scripts/perf/load_test.py`](../scripts/perf/load_test.py) (standard library, threads
  sending GET requests in a loop) on the same runner. Each path is measured on its own, after a 3 s
  warm-up, for 15 s with 1 connection and then 15 s with 10 connections. The internal token is sent,
  so the anonymous throttle does not answer 429.
- **Reading it:** 1 connection shows what one request costs. 10 connections are more than the 3
  gunicorn workers, so latency there includes queueing and requests/s is the ceiling of this box.
  The backend has no response cache; Next.js pages render from tagged `use cache` data.
- **Gate:** the job fails on any error or a p95 above 1000 ms (a regression tripwire).

## Results

Run [43742133221](https://github.com/MaciejZiel/undercut/actions/runs/43742133221), 2026-11-15, on a
GitHub-hosted `ubuntu-latest` runner: AMD EPYC 9V74, 4 vCPUs, 15 GB RAM. The load generator
shares those 4 vCPUs with the stack.

| Path | Connections | Requests/s | p50 ms | p95 ms | p99 ms | Errors |
|---|---:|---:|---:|---:|---:|---:|
| `/api/v1/seasons/` | 1 | 16 | 64 | 69 | 79 | 0 |
| `/api/v1/seasons/` | 10 | 33 | 300 | 350 | 373 | 0 |
| `/api/v1/seasons/2024/` | 1 | 36 | 28 | 30 | 33 | 0 |
| `/api/v1/seasons/2024/` | 10 | 76 | 130 | 155 | 167 | 0 |
| `/api/v1/drivers/` | 1 | 8 | 130 | 143 | 159 | 0 |
| `/api/v1/drivers/` | 10 | 17 | 583 | 679 | 709 | 0 |
| `/api/v1/search/?q=ham` | 1 | 33 | 31 | 33 | 37 | 0 |
| `/api/v1/search/?q=ham` | 10 | 70 | 143 | 166 | 179 | 0 |
| `/api/v1/rounds/2024/1/` | 1 | 47 | 21 | 23 | 26 | 0 |
| `/api/v1/rounds/2024/1/` | 10 | 95 | 104 | 122 | 133 | 0 |
| `/api/v1/standings/drivers/` | 1 | 56 | 18 | 19 | 23 | 0 |
| `/api/v1/standings/drivers/` | 10 | 116 | 85 | 103 | 109 | 0 |
| `/api/v1/rounds/2024/1/analytics/positions/` | 1 | 28 | 35 | 38 | 43 | 0 |
| `/api/v1/rounds/2024/1/analytics/positions/` | 10 | 58 | 172 | 198 | 212 | 0 |
| `/api/v1/rounds/2024/1/replay/` | 1 | 7 | 137 | 152 | 214 | 0 |
| `/api/v1/rounds/2024/1/replay/` | 10 | 16 | 639 | 744 | 789 | 0 |
| `/` | 1 | 67 | 14 | 23 | 28 | 0 |
| `/` | 10 | 88 | 111 | 131 | 219 | 0 |
| `/seasons/2024/1` | 1 | 48 | 19 | 30 | 40 | 0 |
| `/seasons/2024/1` | 10 | 61 | 160 | 202 | 212 | 0 |
| `/drivers` | 1 | 98 | 10 | 18 | 20 | 0 |
| `/drivers` | 10 | 142 | 72 | 81 | 98 | 0 |

## What it shows

- Pages are cheap: the Next.js cache serves `/` and `/drivers` in 10-15 ms (p50).
- The two most expensive API calls are the driver list (a page of 25, but the career counts it
  sorts and filters on are aggregated over every driver and result since 1950, about 130 ms) and
  the replay of a whole race (one document of about 30,000 values, about 140 ms). The `/drivers`
  page reads the list through the Next.js cache; the replay is fetched by the browser once per
  race and kept by TanStack Query.
- Results vary between runs because GitHub assigns different CPUs (an earlier run on an Intel
  Xeon 6975P-C was about 1.5 times faster at 10 connections). Compare rows within one run, not
  across runs.

To reproduce, run the `Perf` workflow from the Actions tab (or `bash scripts/perf/ci.sh` against a
local `make up` stack).
