#!/usr/bin/env bash
# Start the worker (manage.py run_outbox_worker).
# Config comes from the env file; values are never printed.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${UNDERCUT_ENV:-$HOME/.config/undercut/env}

if [ ! -r "$ENV_FILE" ]; then
  echo "undercut: env file not readable: $ENV_FILE" >&2
  exit 1
fi
set -a
. "$ENV_FILE"
set +a

cd "$ROOT/backend"
exec "$ROOT/backend/.venv/bin/python" manage.py run_outbox_worker
