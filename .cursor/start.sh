#!/usr/bin/env bash
# Per-boot runtime initialization for the Agora application.
# Applies database migrations (idempotent). Safe on docs-only branches.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -x .venv/bin/alembic ]; then
  echo "[agora-start] No virtualenv found (docs-only branch or install skipped); nothing to start."
  exit 0
fi

export AGORA_DATABASE_URL="${AGORA_DATABASE_URL:-sqlite+pysqlite:///.agora/agora.db}"
mkdir -p .agora

echo "[agora-start] Applying database migrations ..."
.venv/bin/alembic upgrade head

echo "[agora-start] Ready."
