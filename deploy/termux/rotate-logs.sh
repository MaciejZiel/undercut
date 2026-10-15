#!/usr/bin/env bash
# Keep the service logs from growing without bound (no logrotate on the host).
# For every undercut-*.log above MAX_BYTES: copy it to <name>.1 (replacing the previous copy) and
# truncate the original. The supervisors append with >>, so truncating in place is safe.
# Usage: rotate-logs.sh [log-dir]   (env: MAX_BYTES, default 5 MiB)
set -u
DIR=${1:-$HOME/services/logs}
MAX_BYTES=${MAX_BYTES:-5242880}

for log in "$DIR"/undercut-*.log; do
  [ -f "$log" ] || continue
  size=$(stat -c %s "$log" 2>/dev/null || echo 0)
  if [ "$size" -gt "$MAX_BYTES" ]; then
    cp -f "$log" "$log.1" && : > "$log"
    echo "$(date -u +%FT%TZ) rotated $(basename "$log") ($size bytes)"
  fi
done
