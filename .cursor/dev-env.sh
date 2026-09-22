# Shared local development environment variables for Agora.
# These are non-secret, local-only bootstrap placeholders used to run the app
# against the default SQLite database. Do not use these values in production.
export AGORA_ENV="${AGORA_ENV:-development}"
export AGORA_DATABASE_URL="${AGORA_DATABASE_URL:-sqlite+pysqlite:///.agora/agora.db}"
export AGORA_BOOTSTRAP_ORG_ID="${AGORA_BOOTSTRAP_ORG_ID:-local-org}"
export AGORA_BOOTSTRAP_HUMAN_TOKEN="${AGORA_BOOTSTRAP_HUMAN_TOKEN:-dev-human-token}"
export AGORA_BOOTSTRAP_AGENT_TOKEN="${AGORA_BOOTSTRAP_AGENT_TOKEN:-dev-agent-token}"
export AGORA_BOOTSTRAP_CI_TOKEN="${AGORA_BOOTSTRAP_CI_TOKEN:-dev-ci-token}"
export AGORA_AGENT_TOKEN="${AGORA_AGENT_TOKEN:-dev-agent-token}"
export AGORA_API_URL="${AGORA_API_URL:-http://127.0.0.1:8000}"
export AGORA_WEB_ORIGIN="${AGORA_WEB_ORIGIN:-http://127.0.0.1:3000}"
# The web UI authenticates via browser cookie session, not a bearer token.
export AGORA_WEB_HUMAN_TOKEN="${AGORA_WEB_HUMAN_TOKEN:-}"
