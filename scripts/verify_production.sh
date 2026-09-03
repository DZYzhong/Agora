#!/usr/bin/env bash
# Agora production acceptance check (post-deploy verification).
#
# Runs the deployment-manual §4 checklist as one command:
#   /ready 200 + checks.ok | security headers | /metrics agora_ready
#   web /login 200 | alembic revision | prometheus target up
#   outbox retryable == 0
#
# Usage: scripts/verify_production.sh
# Exit code 0 when every check passes; non-zero otherwise.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/infra/docker-compose.yml")
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker-compose -f "$ROOT/infra/docker-compose.yml")
fi
API="https://127.0.0.1:8443"
WEB="http://127.0.0.1:3000"
EXPECTED_REV="20260902_0019"
fail=0

check() { # check <name> <status> <detail>
  local name="$1" status="$2" detail="$3"
  if [[ "$status" == "PASS" ]]; then echo "PASS  $name"; else echo "FAIL  $name: $detail"; fail=1; fi
}

ready=$(curl -sk -m 10 "$API/ready")
if echo "$ready" | grep -q '"status":"ready"'; then check "api /ready" PASS ""; else check "api /ready" FAIL "$ready"; fi

headers=$(curl -sk -m 10 -D - -o /dev/null "$API/health" 2>/dev/null | tr -d '\r')
sec=0
for h in "x-content-type-options: nosniff" "x-frame-options: DENY" "content-security-policy"; do
  echo "$headers" | grep -qi "$h" || sec=1
done
[[ "$sec" -eq 0 ]] && check "security headers" PASS "" || check "security headers" FAIL "missing on /health"

metrics=$(curl -sk -m 10 "$API/metrics" 2>/dev/null)
echo "$metrics" | grep -q "^agora_ready 1$" && check "metrics agora_ready=1" PASS "" || check "metrics agora_ready=1" FAIL ""

code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$WEB/login")
[[ "$code" == "200" ]] && check "web /login 200" PASS "" || check "web /login 200" FAIL "http $code"

rev=$("${COMPOSE[@]}" exec -T postgres psql -U agora -d agora -tAc "SELECT version_num FROM alembic_version" 2>/dev/null | tr -d '[:space:]')
[[ "$rev" == "$EXPECTED_REV" ]] && check "schema revision $EXPECTED_REV" PASS "" || check "schema revision $EXPECTED_REV" FAIL "got '$rev'"

targets=$(curl -s -m 10 "http://127.0.0.1:9091/api/v1/targets" 2>/dev/null)
if echo "$targets" | grep -q '"health":"up"'; then check "prometheus target up" PASS ""; else check "prometheus target up" FAIL "no up target"; fi

ob=$(echo "$metrics" | grep -E "^agora_outbox_retryable_total [0-9]+$" | awk '{print $2}')
[[ "${ob:-1}" == "0" ]] && check "outbox retryable 0" PASS "" || check "outbox retryable 0" FAIL "retryable=$ob"

if [[ "$fail" -eq 0 ]]; then echo "PRODUCTION ACCEPTANCE PASS"; else echo "PRODUCTION ACCEPTANCE FAIL"; exit 1; fi
