#!/usr/bin/env bash
# Waits until the API reports ready and the home page is served through the proxy.
set -euo pipefail

base="${E2E_BASE_URL:-http://localhost:8080}"
deadline=$((SECONDS + ${WAIT_SECONDS:-240}))

wait_for() {
  local url="$1"
  until curl -fsS -o /dev/null "${url}"; do
    if (( SECONDS > deadline )); then
      echo "Timed out waiting for ${url}" >&2
      return 1
    fi
    sleep 3
  done
  echo "Ready: ${url}"
}

wait_for "${base}/api/ready/"
wait_for "${base}/"
