#!/usr/bin/env bash
# Idempotent repository bootstrap for the Agora application.
# Safe to run on branches that only contain docs (e.g. main); it exits early
# when the application sources are not present on the checked-out revision.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f pyproject.toml ]; then
  echo "[agora-install] No pyproject.toml on this revision (docs-only branch); nothing to set up."
  exit 0
fi

# Python virtualenv support is required to create .venv.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "[agora-install] Installing python3-venv ..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi

echo "[agora-install] Creating virtualenv and installing backend ..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e '.[test]'
# pip-audit is required by the dependency-audit integration tests.
.venv/bin/pip install pip-audit

if [ -d apps/web ]; then
  echo "[agora-install] Installing web dependencies ..."
  (cd apps/web && npm install)
fi

echo "[agora-install] Done."
