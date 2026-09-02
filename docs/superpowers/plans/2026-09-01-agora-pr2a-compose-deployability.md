# Agora PR2A Compose Deployability Fixes

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two deployment defects from the P0-P9 code review (HIGH-2, HIGH-3) so `docker compose` can actually run the API + Web + Local Connector together, with PostgreSQL data surviving container recreation.

**Architecture:** Unify the server-side API base URL under the single runtime variable `AGORA_API_URL` (already read by the MCP Local Connector), used by the Next.js server runtime for all API fetches; declare a named volume for PostgreSQL so data persists across `docker compose down` / `up`.

**Tech Stack:** Docker Compose, Next.js 15, Python, pytest.

**Design source:** `docs/reviews/2026-08-28-agora-p0-p9-code-review.zh-CN.md` (HIGH-2, HIGH-3), `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`.

**Scope boundary:** PR2A covers Compose variable contract and PostgreSQL persistence only. It does not claim the full PR2 exit gate (TLS, worker, DR, measured RPO/RTO), which remains gated behind PR1 exit per the roadmap.

---

## Chunk 1: Single runtime API URL variable

### Task 1: Switch Web fetches to `AGORA_API_URL`

**Files:**

- Modify: `apps/web/lib/api.ts`
- Modify: `infra/docker-compose.yml`
- Modify: `.env.example`
- Modify: `scripts/prepare_p2_blackbox.py`
- Modify: `docs/development/p0-usage-guide.zh-CN.md`
- Modify: `docs/development/p2-real-ai-tool-blackbox.zh-CN.md`
- Modify: `docs/development/p3-context-governance-blackbox.zh-CN.md`
- Modify: `docs/development/p4-workflow-audit-blackbox.zh-CN.md`
- Modify: `docs/manual/agora-system-user-and-technical-manual.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`

- [x] **Step 1: Write failing contract tests**

Tests assert:

- `apps/web/lib/api.ts` reads `AGORA_API_URL` and no longer references `NEXT_PUBLIC_AGORA_API_URL` or `AGORA_API_BASE_URL`.
- Compose `web` and `local-connector` services set `AGORA_API_URL=http://api:8000`.
- No `AGORA_API_BASE_URL` appears anywhere in `infra/docker-compose.yml`.
- Compose `postgres` service declares a named volume mount and the volume is declared at the top level.
- No `NEXT_PUBLIC_AGORA_API_URL` remains in the local-development docs and black-box scripts (single naming convention).

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/test_web_config.py -q
```

Expected: the new contract tests fail against the current source.

- [x] **Step 3: Implement**

- Replace the `NEXT_PUBLIC_AGORA_API_URL` read in `apps/web/lib/api.ts` with `AGORA_API_URL`, keeping `http://localhost:8000` as the fallback. All `lib/api` consumers are server components / route handlers, so a runtime server variable is safe and is not inlined by the Next.js build.
- In `infra/docker-compose.yml`, replace `AGORA_API_BASE_URL` with `AGORA_API_URL: http://api:8000` on `web` and `local-connector`.
- Add `AGORA_API_URL` to `.env.example` with a localhost default for non-Compose runs.
- Replace `NEXT_PUBLIC_AGORA_API_URL` with `AGORA_API_URL` in `scripts/prepare_p2_blackbox.py` and the local-development docs above.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/integration/test_web_config.py -q
```

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/web/lib/api.ts infra/docker-compose.yml .env.example scripts/prepare_p2_blackbox.py docs/development/p0-usage-guide.zh-CN.md docs/development/p2-real-ai-tool-blackbox.zh-CN.md docs/development/p3-context-governance-blackbox.zh-CN.md docs/development/p4-workflow-audit-blackbox.zh-CN.md docs/manual/agora-system-user-and-technical-manual.zh-CN.md tests/integration/test_web_config.py
git commit -m "fix: unify compose API URL variable and persist postgres data"
```

---

## Chunk 2: PostgreSQL persistent storage

### Task 2: Named volume for PostgreSQL

**Files:**

- Modify: `infra/docker-compose.yml`
- Modify: `tests/integration/test_web_config.py`

- [x] **Step 1: Write failing contract test**

Compose `postgres` service must mount `agora-postgres-data:/var/lib/postgresql/data` and a top-level `volumes:` block must declare `agora-postgres-data`.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/test_web_config.py -q
```

- [x] **Step 3: Implement**

- Add `volumes: - agora-postgres-data:/var/lib/postgresql/data` to the `postgres` service.
- Add a top-level `volumes:` declaration for `agora-postgres-data`.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/integration/test_web_config.py -q
```

- [x] **Step 5: Verify compose config**

```bash
docker compose -f infra/docker-compose.yml config -q
```

Expected: exit 0. Note: docker CLI was unavailable in the execution environment; the compose document was instead validated by parsing with PyYAML and asserting the service/volume contract (services: api, web, local-connector, postgres, redis, qdrant, opensearch, neo4j; web/connector `AGORA_API_URL=http://api:8000`; postgres volume and top-level `volumes` present).

- [x] **Step 6: Commit**

```bash
git add infra/docker-compose.yml tests/integration/test_web_config.py
git commit -m "fix: persist postgres data with named volume"
```

---

## Execution record (2026-09-01)

- Commit: `fix: unify compose API URL variable and persist postgres data` (single commit covers Task 1 and Task 2).
- RED evidence: new contract tests failed before implementation — `test_compose_web_and_connector_set_single_runtime_api_url`, `test_web_api_client_reads_runtime_api_url_variable`, `test_local_development_docs_and_scripts_use_single_api_url_variable`, `test_compose_postgres_persists_data_with_named_volume` (4 failed, 28 passed).
- GREEN evidence: focused web-config suite `32 passed`; full Python suite `346 passed, 2 skipped`; `next build` passed; PyYAML compose validation passed; `git diff --check` passed.
- Review evidence: spec review confirmed single `AGORA_API_URL` runtime convention is safe because every `lib/api` consumer is a server component or route handler (no `use client` importers), so the variable is read at runtime and not inlined by the Next.js build.
- State: `implemented` and `automated verified`; PR2A black-box verification on a real Compose host remains pending (docker CLI unavailable here).

## Exit criteria

- `PR2A-COMPOSE-*` evidence recorded: compose variable contract matches API/Web/Connector runtime variables; postgres data survives container recreation.
- Full test suite passes with no regressions.
- Roadmap index updated with PR2A entry; PR2 full exit gate remains open and gated behind PR1 exit.
