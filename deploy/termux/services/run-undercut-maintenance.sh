#!/usr/bin/env bash
# Maintenance loop for hosts without crond (same pattern as the other supervisors in ~/services):
#   - every 5 minutes: check_pipeline (a non-zero result is logged with the problem);
#   - once a day after 02:30 UTC: database backup with retention.
# Start from ~/.termux/boot/start-services. Stop it by sending TERM to its PID.
APP_DIR=${UNDERCUT_DIR:-$HOME/undercut}
LOG_DIR=$HOME/services/logs
LOG=$LOG_DIR/undercut-maintenance.log
STATE=$HOME/.undercut-last-backup
mkdir -p "$LOG_DIR"

echo "$(date -u +%FT%TZ) starting undercut-maintenance" >> "$LOG"
while true; do
  rc=0
  bash "$APP_DIR/deploy/termux/check-pipeline.sh" >> "$LOG" 2>&1 || rc=$?
  [ "$rc" -eq 0 ] || echo "$(date -u +%FT%TZ) check-pipeline rc=$rc" >> "$LOG"

  today=$(date -u +%F)
  now=$(date -u +%H%M)
  if [ "$now" -ge 0230 ] && [ "$(cat "$STATE" 2>/dev/null)" != "$today" ]; then
    if bash "$APP_DIR/deploy/termux/backup.sh" >> "$LOG" 2>&1; then
      echo "$today" > "$STATE"
    else
      echo "$(date -u +%FT%TZ) backup failed, will retry in 5 minutes" >> "$LOG"
    fi
  fi
  sleep 300
done
