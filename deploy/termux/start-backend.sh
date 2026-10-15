#!/usr/bin/env bash
# Start the Django API (gunicorn) on 127.0.0.1:8110 after applying migrations.
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
PY="$ROOT/backend/.venv/bin/python"

"$PY" manage.py migrate --noinput

# exec: the supervisor's child becomes the gunicorn master, so it can be stopped by PID.
exec "$PY" -m gunicorn config.wsgi:application \
  --bind "127.0.0.1:${UNDERCUT_BACKEND_PORT:-8110}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout 30 \
  --graceful-timeout 20 \
  --max-requests 2000 --max-requests-jitter 200 \
  --worker-tmp-dir "${TMPDIR:-/tmp}"
