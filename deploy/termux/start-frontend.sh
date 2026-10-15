#!/usr/bin/env bash
# Start the Next.js standalone server on 127.0.0.1:3110.
# Expects the assembled build in $UNDERCUT_FRONTEND_DIR (default: <repo>/frontend-run),
# containing server.js, .next/static and public (see install.sh and README.md).
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${UNDERCUT_ENV:-$HOME/.config/undercut/env}
APP_DIR=${UNDERCUT_FRONTEND_DIR:-$ROOT/frontend-run}

if [ ! -r "$ENV_FILE" ]; then
  echo "undercut: env file not readable: $ENV_FILE" >&2
  exit 1
fi
set -a
. "$ENV_FILE"
set +a

if [ ! -f "$APP_DIR/server.js" ]; then
  echo "undercut: $APP_DIR/server.js missing; build and install the frontend first" >&2
  exit 1
fi

export NODE_ENV=production
export NEXT_TELEMETRY_DISABLED=1
export HOSTNAME=127.0.0.1
export PORT="${UNDERCUT_FRONTEND_PORT:-3110}"

cd "$APP_DIR"
exec node --max-old-space-size="${NODE_MAX_OLD_SPACE:-192}" server.js
