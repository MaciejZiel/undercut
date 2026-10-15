#!/usr/bin/env bash
# Logical backup of the `undercut` database: pg_dump -Fc into ~/backups/undercut-<UTC timestamp>.dump.
#
# - Refuses to run when free disk space is below UNDERCUT_BACKUP_MIN_FREE_MB (default 2048).
# - Keeps the newest dump of each of the last 7 days and of each of the last 4 ISO weeks.
# - Only ever deletes files named exactly undercut-YYYYMMDDTHHMMSSZ.dump in the backup directory.
#   Hand-named dumps (for example undercut-<sha>.dump from the update checklist) are never touched.
# - Dumps are mode 600. No secrets are printed.
#
# Usage: backup.sh              dump, then prune
#        backup.sh --prune-only prune only (also used to test the retention rule)
# Environment (all optional): UNDERCUT_DB_NAME, UNDERCUT_BACKUP_DIR, UNDERCUT_BACKUP_MIN_FREE_MB,
#   UNDERCUT_KEEP_DAILY, UNDERCUT_KEEP_WEEKLY; libpq variables (PGHOST, PGUSER, ...) are passed on.
# On the server pg_dump connects over the unix socket as the Termux user (no password needed).
set -euo pipefail
umask 077

DB=${UNDERCUT_DB_NAME:-undercut}
DIR=${UNDERCUT_BACKUP_DIR:-$HOME/backups}
MIN_FREE_MB=${UNDERCUT_BACKUP_MIN_FREE_MB:-2048}
KEEP_DAILY=${UNDERCUT_KEEP_DAILY:-7}
KEEP_WEEKLY=${UNDERCUT_KEEP_WEEKLY:-4}
NAME_RE='^undercut-[0-9]{8}T[0-9]{6}Z\.dump$'

log() { echo "$(date -u +%FT%TZ) backup: $*"; }

prune() {
  local f name day week
  local -A seen_day=() seen_week=() keep=()
  local days=0 weeks=0
  # Newest first: the timestamp in the name sorts like time.
  while IFS= read -r f; do
    name=${f##*/}
    [[ $name =~ $NAME_RE ]] || continue
    day=${name:9:8}
    if [[ -z ${seen_day[$day]:-} && $days -lt $KEEP_DAILY ]]; then
      seen_day[$day]=1; days=$((days + 1)); keep[$name]=1
    fi
    week=$(date -u -d "${day:0:4}-${day:4:2}-${day:6:2}" +%G-%V)
    if [[ -z ${seen_week[$week]:-} && $weeks -lt $KEEP_WEEKLY ]]; then
      seen_week[$week]=1; weeks=$((weeks + 1)); keep[$name]=1
    fi
  done < <(find "$DIR" -maxdepth 1 -type f -name 'undercut-*.dump' | sort -r)

  local removed=0
  while IFS= read -r f; do
    name=${f##*/}
    [[ $name =~ $NAME_RE ]] || continue
    if [[ -z ${keep[$name]:-} ]]; then
      # -name with the exact file name: the delete can never match anything else.
      find "$DIR" -maxdepth 1 -type f -name "$name" -delete
      removed=$((removed + 1))
    fi
  done < <(find "$DIR" -maxdepth 1 -type f -name 'undercut-*.dump' | sort)
  log "kept ${#keep[@]} dump(s), removed $removed"
}

mkdir -p "$DIR"
chmod 700 "$DIR"

if [[ ${1:-} == "--prune-only" ]]; then
  prune
  exit 0
fi

free_mb=$(df -Pk "$DIR" | awk 'NR==2 {print int($4 / 1024)}')
if [[ -z $free_mb || $free_mb -lt $MIN_FREE_MB ]]; then
  log "refusing to run: ${free_mb:-unknown} MB free in $DIR, need at least $MIN_FREE_MB MB" >&2
  exit 2
fi

LOCK="$DIR/.undercut-backup.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  log "another backup is running (lock $LOCK); remove the directory only if no backup process exists" >&2
  exit 3
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
final="$DIR/undercut-$stamp.dump"
partial="$DIR/.undercut-$stamp.dump.partial"
trap 'rm -f "$partial"; rmdir "$LOCK" 2>/dev/null || true' EXIT

log "dumping database $DB"
pg_dump -Fc -f "$partial" "$DB"
# A dump that pg_restore cannot even list is useless: fail instead of keeping it.
pg_restore --list "$partial" >/dev/null
chmod 600 "$partial"
mv "$partial" "$final"
size=$(du -k "$final" | cut -f1)
log "wrote $final (${size} KB)"

prune
