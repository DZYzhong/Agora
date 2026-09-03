#!/usr/bin/env bash
# Install a daily encrypted-backup cron job for Agora.
#
#   scripts/install_backup_cron.sh            # install (Linux/macOS crontab)
#   scripts/install_backup_cron.sh --remove   # remove the job
#
# The passphrase is stored in .agora/backup.pass (chmod 600, gitignored) and
# read by the cron job via AGORA_BACKUP_PASSPHRASE — never in argv/logs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARK="# agora-backup-cron"
PASS_FILE="$ROOT/.agora/backup.pass"

if [[ "${1:-}" == "--remove" ]]; then
  crontab -l 2>/dev/null | grep -v "$MARK" | crontab -
  echo "removed agora backup cron job"
  exit 0
fi

if [[ ! -f "$PASS_FILE" ]]; then
  umask 077
  openssl rand -hex 24 > "$PASS_FILE"
  echo "generated passphrase at $PASS_FILE (chmod 600)"
fi

LINE="0 2 * * * AGORA_BACKUP_PASSPHRASE=\$(cat '$PASS_FILE') BACKUP_DIR='$ROOT/.agora/backups' '$ROOT/scripts/backup_db.sh' >> '$ROOT/.agora/backups/cron.log' 2>&1 $MARK"
( crontab -l 2>/dev/null | grep -v "$MARK"; echo "$LINE" ) | crontab -
echo "installed daily 02:00 encrypted backup cron for Agora"
crontab -l | grep "$MARK"
