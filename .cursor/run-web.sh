#!/usr/bin/env bash
# Long-running foreground process: Agora Next.js web UI on :3000.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d apps/web/node_modules ]; then
  echo "[agora-web] Web dependencies not installed; skipping web (docs-only branch or install skipped)."
  exit 0
fi

# shellcheck source=/dev/null
source .cursor/dev-env.sh

cd apps/web
exec npm run dev
