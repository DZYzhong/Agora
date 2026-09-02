#!/usr/bin/env bash
# Agora local production deployment helper.
#
#   scripts/deploy_local.sh            # build/start/wait, print status
#   scripts/deploy_local.sh --bootstrap-admin <admin-username> <admin-password>
#   scripts/deploy_local.sh --smoke     # API-level smoke (requires admin password file)
#
# Requirements: docker (colima on macOS), docker-compose, openssl.
# Secrets: infra/.env is generated on first run with random bootstrap tokens
# (gitignored). Admin bootstrap is a separate one-time step so the operator can
# choose the password; see docs/development/local-production-runbook.zh-CN.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker-compose -f "$ROOT/infra/docker-compose.yml")
CERTS_DIR="$ROOT/.agora/certs"
ENV_FILE="$ROOT/infra/.env"
API_HTTPS="https://127.0.0.1:8443"
WEB_URL="http://127.0.0.1:3000"

gen_secret() { openssl rand -base64 32 | tr -d '/+=' | head -c 40; }

ensure_secrets() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "==> Generating $ENV_FILE with random bootstrap secrets (gitignored)"
    umask 077
    cat > "$ENV_FILE" <<EOF
# Local production secrets for infra/docker-compose.yml (gitignored).
# Generated $(date -u +%F) by scripts/deploy_local.sh; rotate by editing then:
#   docker-compose -f infra/docker-compose.yml up -d api local-connector
AGORA_BOOTSTRAP_HUMAN_TOKEN=$(gen_secret)
AGORA_BOOTSTRAP_AGENT_TOKEN=$(gen_secret)
AGORA_BOOTSTRAP_CI_TOKEN=$(gen_secret)
EOF
  else
    echo "==> Secrets file $ENV_FILE already present (leaving unchanged)"
  fi
}

ensure_certificates() {
  if [[ ! -f "$CERTS_DIR/agora.crt" || ! -f "$CERTS_DIR/agora.key" ]]; then
    echo "==> Generating self-signed TLS certificate for localhost"
    mkdir -p "$CERTS_DIR"
    openssl req -x509 -newkey rsa:2048 -nodes \
      -keyout "$CERTS_DIR/agora.key" -out "$CERTS_DIR/agora.crt" \
      -days 365 -subj "/CN=localhost"
  fi
}

wait_healthy() {
  echo "==> Waiting for api /ready (up to 120s)"
  for _ in $(seq 1 60); do
    if curl -sk -m 5 -o /dev/null "$API_HTTPS/ready"; then
      echo "==> API ready: $API_HTTPS/ready"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: api did not become ready. Check: ${COMPOSE[*]} logs api" >&2
  return 1
}

case "${1:-}" in
  --bootstrap-admin)
    [[ $# -eq 3 ]] || { echo "usage: $0 --bootstrap-admin <username> <password>" >&2; exit 2; }
    "${COMPOSE[@]}" exec -T api python -m scripts.agora_admin bootstrap-admin \
      --database-url "postgresql+psycopg://agora:agora@postgres:5432/agora" \
      --org-id local-org --admin-username "$2" --admin-password "$3"
    ;;
  --smoke)
    curl -sk -m 5 "$API_HTTPS/ready" && echo
    curl -s -m 5 -o /dev/null -w "web /login -> %{http_code}\n" "$WEB_URL/login"
    ;;
  "")
    ensure_secrets
    ensure_certificates
    echo "==> Building and starting Agora stack"
    "${COMPOSE[@]}" up -d --build
    wait_healthy
    echo
    echo "Agora local production stack is up:"
    echo "  Web UI : $WEB_URL  (login as an activated member user)"
    echo "  API    : $API_HTTPS (TLS; /ready /health /metrics)"
    echo "  Admin  : one-time bootstrap with:"
    echo "           $0 --bootstrap-admin <username> <password>"
    echo "  Secrets: $ENV_FILE (gitignored; keep private)"
    ;;
  *)
    echo "usage: $0 [--bootstrap-admin <username> <password>|--smoke]" >&2
    exit 2
    ;;
esac
