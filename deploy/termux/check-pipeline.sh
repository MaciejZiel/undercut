#!/usr/bin/env bash
# Cron wrapper for `manage.py check_pipeline`: loads the env file, runs the check, logs one line.
# Exit code 0 = healthy, 1 = a problem (details in the output), anything else = could not run.
# Config comes from the env file; values are never printed.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${UNDERCUT_ENV:-$HOME/.config/undercut/env}

if [ ! -r "$ENV_FILE" ]; then
  echo "undercut: env file not readable: $ENV_FILE" >&2
  exit 2
fi
set -a
. "$ENV_FILE"
set +a

cd "$ROOT/backend"
rc=0
out=$("$ROOT/backend/.venv/bin/python" manage.py check_pipeline 2>&1) || rc=$?
echo "$(date -u +%FT%TZ) check_pipeline rc=$rc $(echo "$out" | tr '\n' ' ')"
exit "$rc"
