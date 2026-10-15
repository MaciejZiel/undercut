#!/usr/bin/env bash
# Restore the latest dump into a scratch database, run sanity counts, drop the scratch database.
# Runs only when someone starts it (NFR-602); it never touches the live `undercut` database.
#
# Usage: restore-test.sh [dump-file]     default: newest ~/backups/undercut-YYYYMMDDTHHMMSSZ.dump
# Prints RESTORE TEST PASSED or RESTORE TEST FAILED; the exit code matches.
# Environment (optional): UNDERCUT_BACKUP_DIR; libpq variables (PGHOST, PGUSER, ...) are passed on.
set -uo pipefail

DIR=${UNDERCUT_BACKUP_DIR:-$HOME/backups}
SCRATCH=undercut_restore_test   # fixed name on purpose: this is the only database ever dropped
NAME_RE='^undercut-[0-9]{8}T[0-9]{6}Z\.dump$'

dump=${1:-}
if [[ -z $dump ]]; then
  while IFS= read -r f; do
    [[ ${f##*/} =~ $NAME_RE ]] && { dump=$f; break; }
  done < <(find "$DIR" -maxdepth 1 -type f -name 'undercut-*.dump' | sort -r)
fi
if [[ -z $dump || ! -r $dump ]]; then
  echo "RESTORE TEST FAILED: no readable dump found in $DIR" >&2
  exit 2
fi
echo "dump: $dump ($(du -k "$dump" | cut -f1) KB, $(date -u -r "$dump" +%FT%TZ))"

if psql -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '$SCRATCH'" | grep -q 1; then
  echo "RESTORE TEST FAILED: database $SCRATCH already exists; drop it by hand if it is a leftover" >&2
  exit 3
fi

cleanup() { dropdb --if-exists "$SCRATCH" >/dev/null 2>&1; }
trap cleanup EXIT

fail() { echo "RESTORE TEST FAILED: $1" >&2; exit 1; }

createdb "$SCRATCH" || fail "could not create $SCRATCH"
start=$(date +%s)
# Extensions (unaccent, pg_trgm) are part of the dump; ownership and grants are not needed here.
pg_restore --no-owner --no-privileges --exit-on-error -d "$SCRATCH" "$dump" || fail "pg_restore reported errors"
echo "restored in $(($(date +%s) - start)) s"

count() { psql -d "$SCRATCH" -Atqc "SELECT count(*) FROM $1" 2>/dev/null; }

migrations=$(count django_migrations) || true
[[ -n $migrations && $migrations -gt 0 ]] || fail "django_migrations is empty or missing"
echo "django_migrations: $migrations"

for table in accounts_user catalog_season catalog_driver catalog_round catalog_session \
  catalog_result events_outboxevent ingestion_syncrun; do
  n=$(count "$table") || true
  [[ -n $n ]] || fail "table $table is missing or unreadable"
  echo "$table: $n"
done

echo "RESTORE TEST PASSED ($(date -u +%FT%TZ))"
