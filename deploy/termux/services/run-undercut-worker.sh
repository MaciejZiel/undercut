#!/usr/bin/env bash
# Supervisor loop for the Undercut worker: waits for PostgreSQL, runs the app, restarts it after 5 s.
# Install as ~/services/run-undercut-worker.sh (chmod +x) and start it from ~/.termux/boot/start-services.
# Stop the app by sending TERM to its PID (never pgrep -f / pkill -f); this loop starts it again.
APP_DIR=${UNDERCUT_DIR:-$HOME/undercut}
LOG_DIR=$HOME/services/logs
LOG=$LOG_DIR/undercut-worker.log
mkdir -p "$LOG_DIR"

while true; do
  until pg_isready -q -h 127.0.0.1 -p 5432; do
    sleep 2
  done
  echo "$(date -u +%FT%TZ) starting undercut-worker" >> "$LOG"
  rc=0
  bash "$APP_DIR/deploy/termux/start-worker.sh" >> "$LOG" 2>&1 || rc=$?
  echo "$(date -u +%FT%TZ) undercut-worker exited ($rc), restarting in 5 s" >> "$LOG"
  sleep 5
done
