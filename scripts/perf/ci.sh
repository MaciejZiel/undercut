#!/usr/bin/env bash
# Load test run by .github/workflows/perf.yml against the Docker Compose stack on the runner.
# Each path is measured on its own (after a short warm-up) so the table shows per-endpoint
# latency, at two levels: 1 connection (the time one request takes) and 10 connections (more
# than the 3 gunicorn workers, so latency includes queueing and the throughput is the ceiling).
# Writes perf-results.jsonl and perf-summary.md; exits 1 if any run has errors or a p95 above
# PERF_P95_MS (a regression tripwire, not the NFR target, which is checked on the real server).
set -euo pipefail

base="${PERF_BASE_URL:-http://localhost:8080}"
levels="${PERF_CONNECTIONS:-1 10}"
seconds="${PERF_SECONDS:-15}"
p95_ms="${PERF_P95_MS:-1000}"
results="perf-results.jsonl"
rm -f "${results}"

paths=(
  # API (Django + PostgreSQL behind Caddy; no response cache in the backend)
  /api/v1/seasons/
  /api/v1/seasons/2024/
  /api/v1/drivers/
  "/api/v1/search/?q=ham"
  /api/v1/rounds/2024/1/
  /api/v1/standings/drivers/
  /api/v1/rounds/2024/1/analytics/positions/
  /api/v1/rounds/2024/1/replay/
  # Pages (Next.js server rendering with tagged `use cache` data)
  /
  /seasons/2024/1
  /drivers
)

status=0
for path in "${paths[@]}"; do
  echo "::group::${path}"
  python3 scripts/perf/load_test.py "${base}" "${path}" --connections 2 --seconds 3 \
    --p95-ms 100000 --max-errors 1 > /dev/null  # warm-up, not recorded
  for connections in ${levels}; do
    python3 scripts/perf/load_test.py "${base}" "${path}" --connections "${connections}" \
      --seconds "${seconds}" --p95-ms "${p95_ms}" --json "${results}" || status=1
  done
  echo "::endgroup::"
done

python3 scripts/perf/report.py "${results}" > perf-summary.md || status=1
cat perf-summary.md
exit "${status}"
