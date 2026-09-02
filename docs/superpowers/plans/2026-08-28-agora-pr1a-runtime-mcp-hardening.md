# Agora PR1A Runtime and MCP Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close server-path and auth-bypass risks and deliver an honest MCP/Harness protocol 1.1 transport without exposing the not-yet-built PR1B approval or PR1C upload policy.

**Architecture:** Centralize runtime environment policy, make legacy repository import test/development-only and root-contained, and derive MCP advertisement/dispatch from one immutable registry. Protocol 1.1 is negotiated through an HTTP header, requires idempotency for create/complete/submit/close commands, and is emitted by every Harness response producer.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Next.js, MCP stdio, pytest.

**Design source:** `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`

**Safety gate:** PR1A is not suitable for shared or real-data deployment. Agent-submitted artifacts and all HumanConfirmation are rejected until PR1B/PR1C provide typed acknowledgment/grant and upload-policy enforcement.

---

## Chunk 1: Runtime environment and readiness

### Task 1: Central environment policy and supported values

**Files:**

- Create: `packages/core/settings.py`
- Create: `tests/unit/core/test_settings.py`
- Modify: `tests/conftest.py`
- Modify: `.env.example`
- Modify: `infra/docker-compose.yml`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modify: `docs/manual/agora-system-user-and-technical-manual.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`

- [x] **Step 1: Write failing policy tests**

Tests cover:

```python
def test_test_bypass_requires_isolated_test_environment():
    policy = validate_runtime_policy("test", "sqlite+pysqlite:////tmp/agora-test.db", True, None)
    assert policy.auth_bypass is True

def test_production_rejects_bypass_and_local_init_root():
    with pytest.raises(RuntimeConfigurationError):
        validate_runtime_policy("production", "postgresql+psycopg://agora@db/agora", True, None)
    with pytest.raises(RuntimeConfigurationError):
        validate_runtime_policy("production", "postgresql+psycopg://agora@db/agora", False, "/srv/repos")
```

Also assert unknown `local` and `production-like` values fail with a stable `AGORA_ENV_INVALID` code.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/unit/core/test_settings.py -q
```

Expected: import failure because `packages.core.settings` does not exist.

- [x] **Step 3: Implement immutable runtime policy**

- Accept exactly `test`, `development`, `production`.
- Default to `development` when absent.
- Permit bypass only for `test` plus SQLite filename containing `test` or PostgreSQL database ending `_test`.
- Permit `AGORA_LOCAL_INIT_ROOT` only in test/development.
- Resolve and retain an explicit local-init root; never infer `/` or current working directory.
- Expose secret-free `{code, message, field}` configuration diagnostics.

- [x] **Step 4: Migrate configuration examples and docs**

- Replace `production-like` with `production` in `.env.example`, Compose contracts and P9 guide.
- Replace manual `local` examples with `development`.
- Do not enable `AGORA_LOCAL_INIT_ROOT` in production examples.
- Add source-level tests proving all supported values agree.

- [x] **Step 5: Run GREEN**

```bash
.venv/bin/pytest tests/unit/core/test_settings.py tests/integration/test_web_config.py -q
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add packages/core/settings.py tests/unit/core/test_settings.py tests/conftest.py .env.example infra/docker-compose.yml docs/development/p9-operations-readiness-blackbox.zh-CN.md docs/manual/agora-system-user-and-technical-manual.zh-CN.md tests/integration/test_web_config.py
git commit -m "feat: enforce supported runtime environments"
```

**Execution record (2026-08-31):**

- Commits: `945a48f`, `87bd4aa`, `331b5d6`, `ccb0abb`, `f387f5a`.
- RED evidence: initial settings import failed; subsequent boundary suites failed for unsafe paths, symlinks, YAML variants and inherited Compose environment values before implementation.
- GREEN evidence: focused policy/config suite `72 passed`; full suite `308 passed, 2 skipped`; `pip check` and `git diff --check` passed.
- Review evidence: specification review approved; code-quality review approved after three correction rounds.
- State: `implemented` and `automated verified`; no black-box or PR1A exit claim yet.

### Task 2: Startup refusal and complete readiness failure coverage

**Files:**

- Modify: `apps/api/dependencies.py`
- Modify: `apps/api/auth.py`
- Modify: `apps/api/routers/health.py`
- Modify: `apps/api/main.py`
- Modify: `tests/unit/test_health.py`
- Modify: `tests/integration/api/test_auth.py`

- [x] **Step 1: Add failing startup and readiness tests**

Separate tests must prove:

- lifespan startup refuses production bypass;
- lifespan startup refuses production `AGORA_LOCAL_INIT_ROOT`;
- invalid runtime configuration returns `/ready` HTTP 503 with a stable, secret-free error;
- engine creation failure returns 503;
- database query failure returns 503;
- missing Alembic revision returns 503;
- stale Alembic revision compared with code head returns 503;
- valid isolated test returns 200;
- `/health` stays dependency-free.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/unit/test_health.py tests/integration/api/test_auth.py -q
```

Expected: failures because engine creation occurs outside the handler, schema missing/stale does not fail, and readiness always returns 200.

- [x] **Step 3: Implement one pure readiness builder**

- Put policy loading, engine creation, connection and schema comparison inside guarded checks.
- Read expected Alembic head through the existing migration configuration/helper, not a copied revision string.
- Return stable check codes and exception class names only; never include URLs, SQL, paths or secrets.
- Route sets HTTP 503 whenever builder status is `not_ready`.
- Metrics calls the builder directly and emits `agora_ready 0` without requiring a FastAPI response object.
- Lifespan validates policy before database bootstrap.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/unit/core/test_settings.py tests/unit/test_health.py tests/integration/api/test_auth.py -q
```

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/api/dependencies.py apps/api/auth.py apps/api/routers/health.py apps/api/main.py tests/unit/test_health.py tests/integration/api/test_auth.py
git commit -m "fix: refuse unsafe startup and return truthful readiness"
```

**Execution record (2026-08-31):**

- Commits: `3ef536f`, `91a676d`, `5b0d4c6`.
- RED evidence: initial suite `9 failed, 12 passed`; review-driven suites then exposed mutating probes, partial Alembic-head comparison, cleanup leakage and in-memory engine isolation.
- GREEN evidence: final focused review suite `75 passed`; full suite `324 passed, 2 skipped`; `pip check` and `git diff --check` passed.
- Review evidence: specification review approved; code-quality review approved after non-mutating probes, complete migration-head comparison and owned/borrowed probe lifecycles were verified.
- State: `implemented` and `automated verified`; no black-box or PR1A exit claim yet.

## Chunk 2: Legacy repository import containment

### Task 3: Gate every local-initialization API path

**Files:**

- Modify: `apps/api/routers/projects.py`
- Modify: `tests/integration/api/test_initialization_jobs.py`
- Modify: `tests/integration/test_p2_blackbox_setup.py`
- Modify: `tests/e2e/test_p2_harness_loop.py`
- Modify: `tests/integration/api/test_context_governance_api.py`
- Modify: `tests/integration/api/test_harness_api.py`
- Modify: `tests/integration/api/test_p0_usable_api.py`
- Modify: `tests/integration/api/test_sessions_api.py`
- Modify: `tests/integration/api/test_work_items_api.py`
- Modify: `scripts/prepare_p2_blackbox.py`

- [x] **Step 1: Add failing security tests with valid authentication setup**

Production/development tests explicitly remove autouse bypass, configure distinct bootstrap credentials, enter `TestClient(app)` lifespan and authenticate.

Prove production returns route-equivalent 404 for initialize/retry; development/test without root returns `LOCAL_INIT_DISABLED`; outside-root, `..` and symlink escapes return `LOCAL_INIT_PATH_FORBIDDEN`; retry revalidates its stored path; and an allowed Git repository still initializes.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -q
```

Expected: policy tests fail because arbitrary readable paths are accepted.

- [x] **Step 3: Enforce policy before job creation or retry**

- Resolve root and candidate with `Path.resolve(strict=False)`.
- Require candidate equal root or root in candidate parents.
- Evaluate containment before filesystem/analyzer errors to avoid path probing.
- Production returns 404 for initialize and retry.
- Do not persist rejected candidates or include them in errors.

- [x] **Step 4: Update all callers and fixtures**

Every listed test/script that intentionally imports a local fixture sets `AGORA_ENV=test|development` and `AGORA_LOCAL_INIT_ROOT` to the narrow temporary/fixture root. No global root is added.

- [x] **Step 5: Run GREEN**

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py tests/integration/test_p2_blackbox_setup.py tests/e2e/test_p2_harness_loop.py tests/integration/api/test_context_governance_api.py tests/integration/api/test_harness_api.py tests/integration/api/test_p0_usable_api.py tests/integration/api/test_sessions_api.py tests/integration/api/test_work_items_api.py -q
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add apps/api/routers/projects.py tests/integration/api/test_initialization_jobs.py tests/integration/test_p2_blackbox_setup.py tests/e2e/test_p2_harness_loop.py tests/integration/api/test_context_governance_api.py tests/integration/api/test_harness_api.py tests/integration/api/test_p0_usable_api.py tests/integration/api/test_sessions_api.py tests/integration/api/test_work_items_api.py scripts/prepare_p2_blackbox.py
git commit -m "fix: contain legacy repository import paths"
```

**Execution record (2026-09-01):**

- Commit: `3c91314`.
- Recovery note: execution resumed with partial Task3 tests and implementation already present in the worktree, so the original first RED run could not be reconstructed honestly. Additional red-green regressions were added and observed failing before fixes for malformed JSON production disclosure.
- RED evidence: production malformed JSON against `/projects/{project_id}/initialize-local` returned `422` before middleware interception; review probes also exposed request-header, OpenAPI and non-POST `405 Allow: POST` disclosure risks before fixes.
- GREEN evidence: focused initialization suite `18 passed`; Task3 affected integration/e2e suite `63 passed`; full Python suite `332 passed, 2 skipped`; `pip check` and `git diff --check` passed.
- Review evidence: specification review approved after fixing body-parse ordering, request-id response parity and production OpenAPI enumeration; code-quality review approved after expanding hidden legacy path interception from POST-only to all HTTP methods.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

### Task 4: Remove path controls and path disclosure from Web/API

**Files:**

- Modify: `apps/api/routers/projects.py`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Delete: `apps/web/app/projects/[projectId]/initialize/route.ts`
- Delete: `apps/web/app/projects/[projectId]/initialization-jobs/[jobId]/retry/route.ts`
- Modify: `tests/integration/api/test_initialization_jobs.py`
- Modify: `tests/integration/test_web_config.py`

- [x] **Step 1: Add failing redaction and Web tests**

Assert production project/job responses contain no `repo_path`, absolute path or path-bearing error. Assert project page contains no path field, Initialize form, Retry form or route. Legacy history may show status, counts, sanitized remote and timestamps only.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py::test_production_initialization_history_redacts_local_paths tests/integration/test_web_config.py::test_project_page_has_no_server_local_repository_controls -q
```

Expected: FAIL because paths and controls are rendered.

- [x] **Step 3: Implement environment-aware serialization and remove controls**

- Production serializer omits `repo_path` and replaces path-bearing errors with stable codes/messages.
- Development/test may retain path details for fixture diagnostics.
- Remove both Next.js mutation routes and all controls.
- Empty state says context will arrive from an authorized AI tool.

- [x] **Step 4: Run GREEN and Web build**

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py tests/integration/test_web_config.py -q
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: PASS and build succeeds.

- [x] **Step 5: Commit**

```bash
git add apps/api/routers/projects.py apps/web/app/projects/[projectId]/page.tsx apps/web/app/projects/[projectId]/initialize/route.ts apps/web/app/projects/[projectId]/initialization-jobs/[jobId]/retry/route.ts tests/integration/api/test_initialization_jobs.py tests/integration/test_web_config.py
git commit -m "fix: remove server-local repository controls and disclosure"
```

**Execution record (2026-09-01):**

- Commit: `30365eb`.
- RED evidence: production initialization history returned `repo_path`; Web project page still contained local repository path controls and Retry action; production project/job responses also exposed absolute-path remotes, credential-bearing remotes and path-bearing warnings before redaction fixes.
- GREEN evidence: focused Task4 redaction/Web tests passed; initialization/project/Web config suite `50 passed`; full Python suite `334 passed, 2 skipped`; `NEXT_TELEMETRY_DISABLED=1 npm run build` passed; `pip check` and `git diff --check` passed.
- Review evidence: specification review found project `git_remotes`, job `git_remote` and `warnings` disclosure gaps; quality review found production warning-object rendering and stale five-column history layout risks. Both issue sets were fixed and locally reverified. Final review agent handles were unavailable after context transition, so this record does not claim final subagent approval for Task4.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

## Chunk 3: Honest Harness protocol 1.1

### Task 5: Define version negotiation across all response producers

**Files:**

- Modify: `packages/core/services/protocol.py`
- Modify: `packages/domain/schemas.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/api/routers/integrations.py`
- Modify: `scripts/agora_admin.py`
- Modify: `tests/integration/api/test_harness_api.py`
- Modify: `tests/integration/api/test_integrations_api.py`
- Modify: `tests/integration/test_admin_cli.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`

- [x] **Step 1: Add failing negotiation/response tests**

Contract:

- `Agora-Protocol-Version: 1.1` receives `protocol_version=1.1`.
- Missing header is legacy 1.0 and receives `protocol_version=1.0` plus deprecation metadata.
- Unsupported versions and Connector versions below minimum receive HTTP 426 `UPGRADE_REQUIRED` with supported/minimum versions.
- `complete_workflow_step` has `minimum_protocol_version=1.1`; missing/1.0 headers receive HTTP 426 instead of executing it.
- Manifest current is 1.1 and supported is `[1.0, 1.1]`.
- Every Harness/integration response uses the negotiated value, never a hard-coded literal.
- Admin compatibility check validates both versions and minimum Connector behavior.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_integrations_api.py tests/integration/test_admin_cli.py tests/unit/mcp/test_stdio_server.py -q
```

Expected: new 1.1/426 assertions fail against hard-coded 1.0 responses.

- [x] **Step 3: Implement negotiation and response propagation**

- Add typed `ProtocolContext` in `protocol.py`.
- Read `Agora-Protocol-Version` and `Agora-Connector-Version` in an API dependency.
- MCP stdio always sends 1.1 and current Connector version.
- Pass context to response builders; schema defaults are internal-test fallback only.
- Preserve legacy 1.0 API behavior with explicit deprecation metadata.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_integrations_api.py tests/integration/test_admin_cli.py tests/unit/mcp/test_stdio_server.py -q
```

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add packages/core/services/protocol.py packages/domain/schemas.py packages/harness/service.py apps/api/routers/harness.py apps/api/routers/integrations.py scripts/agora_admin.py tests/integration/api/test_harness_api.py tests/integration/api/test_integrations_api.py tests/integration/test_admin_cli.py tests/unit/mcp/test_stdio_server.py
git commit -m "feat: negotiate harness protocol 1.1"
```

**Execution record (2026-09-01):**

- Commit: included with the Task5 code changes as `feat: negotiate harness protocol 1.1`.
- RED evidence: initial Task5 suite failed with 8 expected failures: current protocol responses remained `1.0`, unsupported/old Connector requests reached business logic instead of HTTP 426, `complete-workflow-step` did not enforce protocol 1.1, compatibility manifests still advertised current `1.0`, and stdio `_post` lacked protocol headers. Review-driven RED then failed on explicit old Connector without protocol header, cross-protocol idempotency replay, and in-process MCP workflow calls missing `protocol_version=1.1`. A final stdio RED failed because `agora_complete_workflow_step` was absent from tool listing and dispatch.
- Implementation: added `ProtocolContext`, centralized negotiation, legacy deprecation metadata, minimum protocol enforcement, low Connector rejection, negotiated response propagation for Harness and integration responses, protocol-aware idempotency hashing/errors, MCP stdio 1.1 headers, in-process MCP service protocol propagation, compatibility check reporting, and stdio `agora_complete_workflow_step` advertisement/dispatch.
- GREEN evidence: focused Task5 and review-regression suite `71 passed`; full Python suite `342 passed, 2 skipped`; `pip check`, `npm --prefix apps/web run build`, and `git diff --check` passed.
- Review evidence: first code review found cross-protocol idempotency replay, low Connector legacy bypass, idempotency error version mismatch, and in-process MCP workflow protocol bypass. All were fixed and covered by regression tests. Second review confirmed those fixes and found the stdio `agora_complete_workflow_step` advertisement/dispatch gap; that gap was fixed and verified. The second reviewer could not run pytest in its isolated environment due missing dependencies, so local verification above is the authoritative test evidence.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

### Task 5B: Move close-work Git capture to Local Connector

**Files:**

- Create: `packages/local_connector/development_capture.py`
- Modify: `packages/harness/development_capture.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/schemas.py`
- Modify: `apps/mcp/tools.py`
- Modify: `apps/mcp/server.py`
- Create: `tests/unit/local_connector/test_development_capture.py`
- Modify: `tests/unit/mcp/test_tools.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`
- Modify: `tests/integration/api/test_harness_api.py`

- [x] **Step 1: Add failing server-path, local-capture and hostile-summary tests**

Prove protocol 1.1 rejects `repo_path`/base/head; production rejects legacy path close before Git; development/test legacy path uses explicit root containment; Connector emits bounded relative metadata; and API rejects absolute/traversal/control-character paths, unknown change statuses, over-limit counts/strings, secret patterns and content-like diff bodies.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/unit/local_connector/test_development_capture.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/integration/api/test_harness_api.py -q
```

Expected: server accepts `repo_path` and unvalidated client summaries.

- [x] **Step 3: Implement local capture plus narrow server validation**

- Connector emits only relative changed paths, allowlisted status (`added|modified|deleted|renamed`), dirty state and bounded diff-stat counters; never diff/file content.
- API normalizes POSIX relative paths; rejects empty, absolute, `..`, control characters and credentials/secret patterns.
- Maximum 500 changed entries, 512 bytes per path, 8 KiB agent summary, 8 KiB test summary and 4 KiB diff-stat JSON.
- Harness stores validated structure without filesystem access.
- Legacy 1.0 path behavior exists only for contained development/test fixtures and is deprecated.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/unit/local_connector/test_development_capture.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/integration/api/test_harness_api.py -q
```

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add packages/local_connector/development_capture.py packages/harness/development_capture.py packages/harness/service.py apps/api/routers/harness.py apps/mcp/schemas.py apps/mcp/tools.py apps/mcp/server.py tests/unit/local_connector/test_development_capture.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/integration/api/test_harness_api.py
git commit -m "fix: keep close-work repository capture local"
```

**Execution record (2026-09-01):**

- Commit: `0be0ea9` (fix: keep close-work repository capture local; single commit covers Steps 1-5).
- RED evidence: before implementation the server accepted `repo_path` and unvalidated client summaries; the new boundary tests could not pass against the previous code.
- Implementation: added `packages/local_connector/development_capture.py` emitting only bounded relative metadata (allowlisted `added|modified|deleted|renamed` statuses, dirty flag, diff-stat counters; never diff/file content); refactored `packages/harness/development_capture.py` to accept validated structured files with the legacy server-side git path retained for contained development/test fixtures; `close_work` now accepts a validated `development_update`; API gating rejects `repo_path` under protocol 1.1 (`LOCAL_REPO_PATH_REJECTED`) and in production before any Git access (`LOCAL_REPO_PATH_FORBIDDEN`), and confines legacy paths to an explicit local-init root; MCP stdio schema and dispatch build the capture locally (`AGORA_WORKSPACE_ROOT`/cwd) and never send server paths.
- GREEN evidence: focused Task5B suites — connector capture `5 passed`, MCP tools/stdio and harness API suites all passed; full Python suite `346 passed, 2 skipped` (counts recorded after the final commit).
- Note: `tests/unit/local_connector/__init__.py` and `tests/unit/harness/__init__.py` were added to resolve a pytest basename collision between the two `test_development_capture.py` modules.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

### Task 6: Canonical immutable tool/handler registry

**Files:**

- Create: `packages/core/services/mcp_tools.py`
- Modify: `packages/core/services/protocol.py`
- Modify: `apps/mcp/server.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`

- [x] **Step 1: Add failing registry contract tests**

Assert advertised canonical names equal manifest names and handler keys; deprecated aliases share the registry; schemas use immutable internal mappings/tuples and fresh JSON copies; each remote definition uses its declared API path; parameterized dispatch validates every payload adapter; canonical tools include `agora_complete_workflow_step`; every definition exposes `minimum_protocol_version`, with workflow completion set to 1.1.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/unit/mcp/test_stdio_server.py -q
```

Expected: FAIL because tools and dispatch are independent lists/chains.

- [x] **Step 3: Implement definitions and registry handlers**

Use frozen records with immutable mappings/tuples and handler callables. Local manifest has no API path. Remote handlers consume definition paths; payload adapters live beside definitions.

- [x] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py -q
```

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add packages/core/services/mcp_tools.py packages/core/services/protocol.py apps/mcp/server.py tests/unit/mcp/test_stdio_server.py
git commit -m "refactor: unify mcp definitions and dispatch"
```

**Execution record (2026-09-01):**

- Commit: `6d1788c` (refactor: unify mcp definitions and dispatch; single commit covers Steps 1-5).
- Implementation: added `packages/core/services/mcp_tools.py` with frozen `McpToolDefinition` records (immutable `properties`/`required` tuples, fresh deep-copied schemas, declared `api_path`, `minimum_protocol_version` and payload adapters beside each definition); `protocol.py` manifest canonical/deprecated lists now derive from the registry; `apps/mcp/server.py` advertises and dispatches solely through the registry (remote tools post to their declared path, deprecated tools carry deprecation metadata, local manifest has no API path).
- GREEN evidence: focused registry/stdio/tools suite `33 passed`; full Python suite counts recorded after the final commit.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

### Task 7: Protocol 1.1 idempotency for create/complete/submit/close tools

**Files:**

- Create: `apps/api/idempotency.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/server.py`
- Modify: `packages/core/services/mcp_tools.py`
- Modify: `tests/integration/api/test_harness_api.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`

- [x] **Step 1: Add failing parameterized tests**

Cover `start_work`, `prepare_context`, `submit_context_proposal`, `complete_workflow_step`, `submit_skill_candidate`, `record_evidence`, `close_work`: 1.1 without key fails; same key/payload replays original status/body without duplicate ContextPacks, rows or events; changed payload conflicts; 1.0 remains temporarily accepted only for tools whose `minimum_protocol_version` is 1.0; 1.0 workflow completion receives 426; MCP requires `idempotency_key` and forwards it as header only. The protocol version is included in the idempotency operation scope and request hash; reusing one key across 1.0 and 1.1 cannot replay a response from the other version and must return a deterministic conflict or independent version-scoped record.

- [x] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/mcp/test_stdio_server.py -q
```

Expected: only start-work has partial idempotency and MCP forwards no key.

- [x] **Step 3: Extract generic API idempotency executor**

Reuse existing record/repository methods. Executor owns request hash, pending/completed replay, conflict and response status/body. Endpoints supply operation and transaction-safe callback. Preserve start behavior while removing its duplicate helper.

- [x] **Step 4: Require and forward MCP keys**

All MCP requests also send protocol and Connector version headers.

- [x] **Step 5: Run GREEN**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py -q
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add apps/api/idempotency.py apps/api/routers/harness.py apps/mcp/server.py packages/core/services/mcp_tools.py tests/integration/api/test_harness_api.py tests/unit/mcp/test_stdio_server.py
git commit -m "feat: require idempotency for protocol 1.1 writes"
```

**Execution record (2026-09-01):**

- Commit: `feat: require idempotency for protocol 1.1 writes` (single commit covers Steps 1-6).
- Implementation: added `apps/api/idempotency.py` with a generic protocol-aware executor (request hash includes protocol version; pending/completed replay; deterministic `IDEMPOTENCY_CONFLICT` on changed payload or cross-protocol reuse; `IDEMPOTENCY_KEY_REQUIRED` for protocol 1.1 writes without a key). The seven write endpoints (`start_work`, `prepare_context`, `submit_context_proposal`, `complete_workflow_step`, `submit_skill_candidate`, `record_evidence`, `close_work`) now run through the executor, replacing the start-work-only helper; responses are normalized to JSON-storable structures before persistence (datetimes to ISO strings). The MCP registry requires `idempotency_key` on the seven write tools and `_dispatch` forwards it as an `Idempotency-Key` header only, never in the body.
- GREEN evidence: focused idempotency suite `5 passed`; API integration suite `112 passed`; full Python suite counts recorded after the final commit.
- Note: existing 1.1-header API tests were updated to send unique `Idempotency-Key` values; the transaction-boundaries test now accepts routes that delegate their committing UoW to `execute_idempotent`.
- State: `implemented` and `automated verified`; PR1A black-box and exit criteria remain pending.

## Chunk 4: MCP workflow transport without false approval

### Task 8: Expose safe workflow completion and block premature content channels

**Files:**

- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/server.py`
- Modify: `packages/core/services/mcp_tools.py`
- Modify: `tests/integration/api/test_harness_api.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`

- [ ] **Step 1: Add failing boundary tests**

In `production`, for every principal kind: summary-only complete succeeds when otherwise authorized; non-empty artifacts returns `PR1_UPLOAD_POLICY_REQUIRED`; any confirmation returns `PR1_APPROVAL_POLICY_REQUIRED`. Legacy artifact/confirmation compatibility is allowed only in isolated `AGORA_ENV=test`, never in development or production. MCP 1.1 schema exposes only idempotency key, session ID, step key and summary.

- [ ] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_agent_workflow_completion_blocks_untyped_artifacts_and_confirmation tests/unit/mcp/test_stdio_server.py::test_stdio_complete_workflow_step_has_pr1a_safe_schema -q
```

Expected: FAIL because API accepts untyped content and stdio omits the tool.

- [ ] **Step 3: Implement temporary safety boundary and handler**

Stdio sends empty artifacts/no confirmation. API checks runtime environment and payload before persistence, independent of principal kind. PR1B/PR1C replace temporary errors with typed policy, never remove checks blindly.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/harness.py apps/mcp/server.py packages/core/services/mcp_tools.py tests/integration/api/test_harness_api.py tests/unit/mcp/test_stdio_server.py
git commit -m "feat: expose safe workflow completion over mcp"
```

### Task 9: Stateful real-stdio process workflow

**Files:**

- Modify: `tests/integration/mcp/test_local_connector_process.py`

- [ ] **Step 1: Add failing stateful process test**

In one real MCP process/session: list 1.1 tools; start with idempotency key; complete returned session; close it; assert ordered API paths, Agent auth, protocol/Connector/idempotency headers, and absence of absolute path, remote credential and source content. Calculate repository root from `Path(__file__).resolve()`, removing hard-coded `PYTHONPATH`.

- [ ] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/integration/mcp/test_local_connector_process.py::test_stdio_process_completes_stateful_protocol_1_1_workflow -q
```

Expected: FAIL because completion and headers are unavailable.

- [ ] **Step 3: Adjust only the stateful recorder fixture**

Do not add production behavior in this step.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/pytest tests/integration/mcp/test_local_connector_process.py tests/unit/mcp/test_stdio_server.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/mcp/test_local_connector_process.py
git commit -m "test: verify stateful mcp 1.1 workflow process"
```

## Chunk 5: Verification and durable evidence

### Task 10: PR1A self-test and black-box preparation

**Files:**

- Create: `docs/development/pr1a-runtime-mcp-blackbox.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`
- Modify: `docs/superpowers/plans/2026-08-28-agora-pr1a-runtime-mcp-hardening.md`
- Modify: `docs/superpowers/plans/2026-08-28-agora-production-readiness-implementation.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [ ] **Step 1: Add failing documentation contract test**

Guide uses AI tool/Web actions only and states PR1A is non-production/non-sensitive; Web has no path/retry controls; AI tool sees 1.1 and summary-only completion; start -> complete -> close works; Web shows state; artifact/confirmation remain blocked pending PR1B/PR1C.

- [ ] **Step 2: Run RED, write guide, run GREEN**

```bash
.venv/bin/pytest tests/integration/test_web_config.py::test_pr1a_blackbox_guide_exists -q
```

- [ ] **Step 3: Run complete PR1A verification**

```bash
.venv/bin/pytest
.venv/bin/python -m compileall -q apps packages scripts alembic
.venv/bin/pip check
cd apps/web && npm run lint
cd apps/web && npx tsc --noEmit
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
git diff --check
```

If no lint script exists, add one or record the exact gap; do not call build lint. PostgreSQL skips before PR2 are partial PR1A evidence only and cannot satisfy release CI.

- [ ] **Step 4: Update durable status honestly**

Record RED/GREEN commands, full counts, build and skips. Mark only PR1A `implemented` and `automated verified`; leave black-box, PR1 exit and production false.

- [ ] **Step 5: Commit**

```bash
git add docs/development/pr1a-runtime-mcp-blackbox.zh-CN.md tests/integration/test_web_config.py docs/superpowers/plans/2026-08-28-agora-pr1a-runtime-mcp-hardening.md docs/superpowers/plans/2026-08-28-agora-production-readiness-implementation.md docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md
git commit -m "docs: record pr1a verification and black-box guide"
```
