#!/usr/bin/env bash
# Loads the data the tests need into the running stack:
#   1. the real history from the free Jolpica dump,
#   2. analytics for one race (2024 round 1) from the OpenF1 API, retried because the free API
#      rate-limits,
#   3. the deterministic prediction round (seed_e2e).
set -euo pipefail

manage() {
  docker compose exec -T backend python manage.py "$@"
}

echo "::group::import_history"
manage import_history --download
echo "::endgroup::"

echo "::group::import_openf1 2024:1"
attempts=3
for attempt in $(seq 1 "${attempts}"); do
  if manage import_openf1 --round 2024:1 --types RACE; then
    break
  fi
  if (( attempt == attempts )); then
    echo "OpenF1 import failed ${attempts} times" >&2
    exit 1
  fi
  echo "OpenF1 import failed (attempt ${attempt}), retrying in 20 s"
  sleep 20
done
echo "::endgroup::"

echo "::group::seed_e2e"
manage seed_e2e
echo "::endgroup::"
