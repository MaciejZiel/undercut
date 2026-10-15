#!/usr/bin/env bash
# Install backend dependencies into backend/.venv, collect static files and (optionally)
# build the frontend on this machine.
#
# Usage:
#   deploy/termux/install.sh            # backend only
#   deploy/termux/install.sh frontend   # backend + build the frontend here (slow, memory hungry)
#
# Prerequisites (Termux): pkg install python clang make libpq postgresql nodejs-lts
#   - clang, make, and pg_config (from the `postgresql` package) plus libpq are needed because
#     psycopg[binary] ships no aarch64 Android wheel. The binary extra is therefore replaced by
#     psycopg[c], which compiles against the system libpq.
#   - Python >= 3.13 is required by backend/pyproject.toml.
#   - If compilation fails on an Android API level error, try: export ANDROID_API_LEVEL=36
#
# The dependency list is read from backend/pyproject.toml (nothing is added or changed there);
# only the psycopg extra is swapped at install time. uv.lock is not used by this script.
#
# Building the frontend on the laptop and copying it over is preferred, see
# deploy/termux/README.md ("Frontend build"). It avoids a long, memory hungry build here.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${UNDERCUT_ENV:-$HOME/.config/undercut/env}
BACKEND="$ROOT/backend"

if [ ! -d "$BACKEND/.venv" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv "$BACKEND/.venv"
  else
    python -m venv "$BACKEND/.venv"
  fi
fi
PY="$BACKEND/.venv/bin/python"

REQS=$(mktemp "${TMPDIR:-/tmp}/undercut-reqs.XXXXXX")
trap 'rm -f "$REQS"' EXIT
"$PY" - "$BACKEND/pyproject.toml" > "$REQS" <<'PYEOF'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    deps = tomllib.load(fh)["project"]["dependencies"]
for dep in deps:
    print(dep.replace("psycopg[binary]", "psycopg[c]"))
PYEOF

if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$PY" -r "$REQS"
else
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r "$REQS"
fi

# collectstatic needs the settings to import; the env file supplies them (values are not printed).
if [ -r "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
else
  echo "undercut: $ENV_FILE not found; collectstatic uses default settings" >&2
fi
(cd "$BACKEND" && "$PY" manage.py collectstatic --noinput)

if [ "${1:-}" = "frontend" ]; then
  FRONT="$ROOT/frontend"
  RUN="${UNDERCUT_FRONTEND_DIR:-$ROOT/frontend-run}"
  (
    cd "$FRONT"
    export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=1536}"
    export NEXT_TELEMETRY_DISABLED=1
    npm ci
    npm run build
  )
  # Output is Next "standalone": server.js + minimal node_modules; static assets and public/
  # must be copied next to it.
  mkdir -p "$RUN"
  cp -R "$FRONT/.next/standalone/." "$RUN/"
  mkdir -p "$RUN/.next"
  cp -R "$FRONT/.next/static" "$RUN/.next/"
  if [ -d "$FRONT/public" ]; then
    cp -R "$FRONT/public" "$RUN/"
  fi
  echo "undercut: frontend installed in $RUN"
fi

echo "undercut: install finished"
