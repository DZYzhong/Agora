#!/usr/bin/env bash
# Agora encrypted PostgreSQL backup (local, rotation 7).
#
#   scripts/backup_db.sh                 # backup to .agora/backups/, keep 7
#   AGORA_BACKUP_PASSPHRASE=...           # passphrase via env (required)
#   BACKUP_DIR=/secure/path scripts/backup_db.sh   # override destination
#
# NOTE: the encrypted file must ALSO be copied off-host/off-VM (operator
# duty) to satisfy DR; this script guarantees the on-host encrypted copy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${AGORA_BACKUP_PASSPHRASE:?set AGORA_BACKUP_PASSPHRASE (env, never argv)}"
DIR="${BACKUP_DIR:-$ROOT/.agora/backups}"
KEEP="${KEEP:-7}"
mkdir -p "$DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$DIR/agora-${STAMP}.enc"
docker-compose -f "$ROOT/infra/docker-compose.yml" exec -T -e BP="$AGORA_BACKUP_PASSPHRASE" postgres \
  sh -c 'pg_dump -U agora -d agora | openssl enc -aes-256-cbc -pbkdf2 -pass env:BP -out /agora_tmp.enc'
docker cp infra-postgres-1:/agora_tmp.enc "$OUT"
docker-compose -f "$ROOT/infra/docker-compose.yml" exec -T postgres sh -c 'rm -f /agora_tmp.enc'
chmod 600 "$OUT"
# rotation: keep the newest $KEEP files
ls -1t "$DIR"/agora-*.enc 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "backup: $OUT ($(wc -c < "$OUT") bytes); kept $(ls -1 "$DIR"/agora-*.enc 2>/dev/null | wc -l | tr -d ' ') file(s)"
