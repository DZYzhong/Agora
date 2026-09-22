#!/usr/bin/env bash
# Long-running foreground process: Agora FastAPI backend on :8000.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -x .venv/bin/uvicorn ]; then
  echo "[agora-api] No virtualenv found; skipping API (docs-only branch or install skipped)."
  exit 0
fi

# shellcheck source=/dev/null
source .cursor/dev-env.sh

exec .venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
