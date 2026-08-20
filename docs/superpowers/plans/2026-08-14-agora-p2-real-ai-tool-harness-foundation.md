# Agora P2 Real AI Tool Harness Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the P1 local trial into an authenticated, idempotent AI-tool-first Harness that resolves a customer-local repository to a Project and WorkItem, creates a WorkSession, and returns a traceable token-budgeted provisional ContextBundle without losing existing data.

**Architecture:** Preserve the FastAPI, SQLAlchemy, Next.js, Harness and stdio MCP foundations. Add new identity and work tables through Alembic, copy legacy TaskSession data without changing historical session IDs, move transaction ownership to request/application Unit of Work boundaries, and make the MCP process the Local Connector that observes Git locally and sends only sanitized metadata. Keep P1 ContextPack data as explicitly provisional input until P3 introduces accepted ContextRevision.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite/Postgres, MCP stdio, Next.js, pytest.

**Canonical references:**

- `docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`
- `docs/superpowers/specs/2026-08-14-agora-technical-architecture-design.zh-CN.md`
- `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

**Compatibility rules:**

- Never delete or rewrite the existing `.agora/agora.db` before a successful migration and backup.
- Preserve existing Project, Asset, ContextPack, Skill, SkillRun, Writeback and SessionEvent records.
- Copy each legacy `task_sessions.id` to the corresponding `work_sessions.id`, preserving all existing references.
- Keep legacy `/harness/plan-context` and old Session Web URLs as compatibility adapters during P2; do not advertise the old MCP tool to new AI clients.
- Do not expose server-side local repository scanning, Fake LLM, Fake keyword search or Fake vector search as the P2 black-box product path.
- Do not introduce ContextRevision, approval merging, configurable WorkflowVersion or SkillVersion early; expose their capability flags as unavailable until P3-P5.

---

## Chunk 1: Persistence, Transactions and Identity

### Task 1: Protect and migrate existing P1 data

**Files:**

- Create: `alembic/versions/20260814_0002_p2_harness_foundation.py`
- Create: `packages/core/schema_manager.py`
- Modify: `packages/core/models.py`
- Modify: `packages/domain/enums.py`
- Modify: `apps/api/dependencies.py`
- Modify: `scripts/agora_admin.py`
- Test: `tests/integration/test_p2_migration.py`
- Test: `tests/integration/test_migrations.py`

- [ ] **Step 1: Write a failing migration preservation test**

Cover both migration entry states: a database at revision `20260813_0001`, and the real P1 shape created by `Base.metadata.create_all()` with no `alembic_version` table. Insert two projects, assets, a ContextPack, Skills, SkillRuns, Writebacks, SessionEvents and multiple TaskSessions sharing one `task_id`, then upgrade to head. Assert all original rows remain and:

```python
assert work_item_count == 2  # shared external task plus one task-less legacy session
assert work_session_ids == legacy_task_session_ids
assert session_event_count == original_event_count
assert writeback_session_ids == legacy_task_session_ids
assert skill_run_session_ids == legacy_task_session_ids
```

Also create a database with an unknown/partial schema and assert migration refuses to mutate it.

- [ ] **Step 2: Run the migration tests and verify they fail**

Run: `.venv/bin/pytest tests/integration/test_p2_migration.py tests/integration/test_migrations.py -v`

Expected: FAIL because revision `20260814_0002` and the new tables do not exist.

- [ ] **Step 3: Implement explicit ownership of existing P1 schemas**

Replace startup `Base.metadata.create_all()` with a schema manager:

```text
new empty database -> alembic upgrade head
known unversioned P1 schema -> create timestamped backup -> verify exact schema fingerprint -> stamp 20260813_0001 -> upgrade head
known versioned schema -> alembic upgrade head
unknown or partial schema -> refuse startup with MIGRATION_REQUIRED and leave the database untouched
```

SQLite backup uses its online backup API rather than copying a live file. Postgres requires an operator backup confirmation in production-like mode. `scripts/agora_admin.py migrate` exposes dry-run, backup path and schema fingerprint diagnostics.

- [ ] **Step 4: Add additive P2 tables and legacy-copy migration**

Add ORM models and migration tables for:

```text
users
credentials
project_memberships
work_items
work_sessions
idempotency_records
```

Required constraints:

```text
credentials.token_hash UNIQUE
project_memberships(project_id, user_id) UNIQUE
work_items(project_id, external_key) UNIQUE when external_key is present
idempotency_records(credential_id, operation, idempotency_key) UNIQUE
```

`IdempotencyRecord` is the only authority for command-key uniqueness and contains `user_id`, `credential_id`, `operation`, `idempotency_key`, `request_hash`, canonical `response_json`, `status`, `replay_expires_at` and timestamps. WorkSession may retain a diagnostic `initial_request_id`, but it does not own a uniqueness constraint. After replay expiry, retain a key tombstone and return `IDEMPOTENCY_KEY_EXPIRED`; require a new key rather than silently reusing an old key for a different command.

Migration rules:

- Group legacy TaskSessions with the same non-null `(project_id, task_id)` into one WorkItem.
- Create one deterministic legacy WorkItem per task-less TaskSession.
- Copy TaskSession rows into WorkSession using the same IDs and timestamps.
- Backfill migrated WorkSessions with the organization placeholder `user_id`, nullable `credential_id`, nullable `initial_request_id` and `legacy_imported=true`. New WorkSessions require a credential and command idempotency record at the application boundary.
- Retain the `task_sessions` table as read-only compatibility storage during P2.
- Seed one disabled-placeholder local user per legacy organization; Task 3 activates configured principals and memberships.

Migration assertions must verify every legacy WorkSession has a valid user foreign key, null credential/request fields, and unchanged SkillRun/Writeback/SessionEvent linkage. Model and migration tests must also assert every required IdempotencyRecord field, foreign key and unique constraint above.

- [ ] **Step 5: Run migration preservation and downgrade/upgrade tests**

Run: `.venv/bin/pytest tests/integration/test_p2_migration.py tests/integration/test_migrations.py -v`

Expected: PASS; no P1 row or historical relationship is lost.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260814_0002_p2_harness_foundation.py packages/core/schema_manager.py packages/core/models.py packages/domain/enums.py apps/api/dependencies.py scripts/agora_admin.py tests/integration/test_p2_migration.py tests/integration/test_migrations.py
git commit -m "feat: add p2 compatible work and identity schema"
```

### Task 2: Move transaction ownership to Unit of Work boundaries

**Files:**

- Create: `packages/core/uow.py`
- Modify: `apps/api/dependencies.py`
- Modify: `packages/core/repositories/projects.py`
- Modify: `packages/core/repositories/assets.py`
- Modify: `packages/core/repositories/initialization_jobs.py`
- Modify: `packages/core/repositories/context_packs.py`
- Modify: `packages/core/repositories/sessions.py`
- Modify: `packages/core/repositories/skills.py`
- Modify: `packages/core/repositories/writebacks.py`
- Modify: `packages/core/services/writebacks.py`
- Modify: `apps/api/routers/*.py`
- Modify: `apps/workers/**/*.py`
- Test: `tests/unit/core/test_uow.py`
- Test: `tests/unit/core/test_repositories.py`
- Test: `tests/integration/api/test_transaction_boundaries.py`

- [ ] **Step 1: Write failing rollback and commit tests**

Cover these cases:

```python
with pytest.raises(ExpectedFailure):
    with SqlAlchemyUnitOfWork(session):
        project_repo.add(...)
        work_repo.add(...)
        raise ExpectedFailure()
assert project_repo.list() == []

with SqlAlchemyUnitOfWork(session):
    project_repo.add(...)
assert project_repo.list() != []
```

Also prove a command can flush Project, WorkItem and WorkSession, then fail, and still leave none of them behind.

- [ ] **Step 2: Run tests and verify partial writes currently survive or repositories commit too early**

Run: `.venv/bin/pytest tests/unit/core/test_uow.py tests/integration/api/test_transaction_boundaries.py -v`

Expected: FAIL because repositories own commits.

- [ ] **Step 3: Implement Unit of Work and remove repository commits**

Implement `SqlAlchemyUnitOfWork` with `flush`, `commit`, rollback-on-exception and nested-command protection. Repository and domain-service mutation methods may `add`, `flush` and `refresh`, but must not commit. The database dependency owns session lifetime only; each application command handler explicitly enters one Unit of Work.

- [ ] **Step 4: Update direct worker and service call sites**

Use `rg -n "\.commit\(" apps packages` as the migration inventory. Wrap every HTTP mutation command, worker activity, admin command and other non-HTTP mutation in one explicit Unit of Work. Do not add a `commit_on_write` compatibility switch. Add a guard test that fails if repository or domain-service modules regain direct commits.

- [ ] **Step 5: Run focused and full repository tests**

Run: `.venv/bin/pytest tests/unit/core/test_uow.py tests/unit/core/test_repositories.py tests/integration/api/test_transaction_boundaries.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/uow.py apps/api/dependencies.py apps/api/routers apps/workers packages/core/repositories packages/core/services/writebacks.py tests/unit/core tests/integration/api/test_transaction_boundaries.py
git commit -m "refactor: own writes at unit of work boundaries"
```

### Task 3: Add the minimum authenticated human and AI-tool boundary

**Files:**

- Create: `packages/core/auth.py`
- Create: `packages/core/repositories/identities.py`
- Create: `apps/api/auth.py`
- Modify: `apps/api/main.py`
- Modify: `apps/api/dependencies.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/api/routers/projects.py`
- Modify: `apps/api/routers/assets.py`
- Modify: `apps/api/routers/sessions.py`
- Modify: `apps/api/routers/skills.py`
- Modify: `apps/api/routers/writebacks.py`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/mcp/server.py`
- Modify: `.env.example`
- Test: `tests/unit/core/test_auth.py`
- Test: `tests/integration/api/test_auth.py`
- Test: `tests/integration/test_web_config.py`

- [ ] **Step 1: Write failing authentication and authorization tests**

Prove:

- Missing and invalid bearer tokens return stable `AUTH_REQUIRED`/`INVALID_CREDENTIAL` errors.
- Human and agent tokens resolve to separate credential kinds for the same user.
- A non-member cannot read or start work in a project.
- A credential cannot plan/fetch/record/close/prepare-writeback against a Session whose Project is outside its membership.
- An agent credential cannot create/archive projects or perform human-only actions.
- `org_id` supplied in payload cannot override the authenticated principal organization.
- Tokens are stored only as SHA-256 hashes with a non-secret prefix for diagnostics.
- Multiple legacy organizations without explicit `AGORA_BOOTSTRAP_ORG_ID` fail closed as ambiguous.
- Creating a Project and its creator's ProjectMembership happens in the same transaction.

- [ ] **Step 2: Run auth tests and verify they fail**

Run: `.venv/bin/pytest tests/unit/core/test_auth.py tests/integration/api/test_auth.py -v`

Expected: FAIL because no principal boundary exists.

- [ ] **Step 3: Implement local-team bootstrap identities and bearer auth**

Create an immutable runtime `Principal` containing `user_id`, `credential_id`, credential kind, organization and project roles; `Principal` is not a persistence key. Persist WorkSession ownership as non-null `user_id` plus nullable-for-legacy `credential_id`. Read `AGORA_BOOTSTRAP_HUMAN_TOKEN`, `AGORA_BOOTSTRAP_AGENT_TOKEN` and `AGORA_BOOTSTRAP_ORG_ID`, hash and upsert credentials at startup, and grant the configured local bootstrap user membership to existing projects in that organization. If the organization is omitted, use the only existing organization, create `local-org` for an empty database, or fail closed when multiple organizations exist. Production-like paths must reject missing tokens; tests may explicitly enable `AGORA_TEST_AUTH_BYPASS=1`, but black-box services must not.

- [ ] **Step 4: Enforce project scope and credential kind**

All project-scoped API commands, including every Harness command, derive organization and user from `Principal`. Session-based commands first resolve WorkSession, then verify its ProjectMembership before reading or mutating anything. Web server fetches attach `AGORA_WEB_HUMAN_TOKEN`; MCP requests attach `AGORA_AGENT_TOKEN`. Never serialize either token to browser HTML, logs or API responses.

- [ ] **Step 5: Run auth, API and Web configuration tests**

Run: `.venv/bin/pytest tests/unit/core/test_auth.py tests/integration/api/test_auth.py tests/integration/test_web_config.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/auth.py packages/core/repositories/identities.py apps/api apps/web/lib/api.ts apps/mcp/server.py .env.example tests/unit/core/test_auth.py tests/integration/api/test_auth.py tests/integration/test_web_config.py
git commit -m "feat: add local team principal boundary"
```

---

## Chunk 2: Work Model and Local Connector Protocol

### Task 4: Replace TaskSession behavior with WorkItem and WorkSession

**Files:**

- Create: `packages/core/repositories/work.py`
- Create: `packages/harness/work_resolver.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `packages/harness/session_recorder.py`
- Modify: `packages/harness/task_resolver.py`
- Modify: `apps/api/routers/sessions.py`
- Create: `apps/api/routers/work_items.py`
- Modify: `apps/api/main.py`
- Test: `tests/unit/harness/test_work_resolver.py`
- Test: `tests/unit/harness/test_harness_service.py`
- Test: `tests/integration/api/test_work_items_api.py`
- Test: `tests/integration/api/test_sessions_api.py`

- [ ] **Step 1: Write failing WorkItem resolution and idempotency tests**

Cover explicit task IDs, branch-derived hints, Chinese software R&D task titles, ambiguous tasks that require clarification, and two users sharing one WorkItem. Verify:

- WorkItem always belongs to a Project already authorized for the Principal.
- WorkSession `user_id` and `credential_id` are derived only from the authenticated Principal and cannot be supplied in the request.
- Retrying the same operation, Principal, key and request hash replays the stored response and returns the same WorkSession.
- Reusing the same key with a different payload returns `IDEMPOTENCY_CONFLICT`.
- Concurrent requests using the same key create one WorkSession and replay one response.
- A new key creates a new WorkSession under the same WorkItem.
- Replay expiry is explicit; expired keys become tombstones returning `IDEMPOTENCY_KEY_EXPIRED`, and cleanup cannot make an old key silently reusable.

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `.venv/bin/pytest tests/unit/harness/test_work_resolver.py tests/integration/api/test_work_items_api.py -v`

Expected: FAIL because WorkItem APIs and resolver do not exist.

- [ ] **Step 3: Implement the authoritative work model**

Implement:

```text
WorkItem: project, external_key, title, status, stage, owner, source
WorkSession: work_item, principal, credential, agent_type, intent, status, idempotency_key
```

`agora_start_work` resolves Project first, then resolves or asks for a WorkItem title, then creates/resumes WorkSession. It returns capability-gated nullable version IDs and does not fabricate ContextRevision/WorkflowVersion/SkillVersion.

Use operation-scoped `IdempotencyRecord` keyed by authenticated `credential_id`, command type and idempotency key. Store `user_id` for audit plus the canonical request hash, canonical response, status and replay expiry in the same transaction as the domain mutation. Runtime Principal data is always derived from the credential and is never accepted from payload fields. The IdempotencyRecord unique constraint is authoritative; WorkSession has no competing key uniqueness rule.

- [ ] **Step 4: Keep P1 Session pages readable through compatibility serializers**

The old Session API and URLs read from WorkSession and include WorkItem details. Do not create new TaskSession rows after this task.

- [ ] **Step 5: Run work model, Harness and Session regression tests**

Run: `.venv/bin/pytest tests/unit/harness/test_work_resolver.py tests/unit/harness/test_harness_service.py tests/integration/api/test_work_items_api.py tests/integration/api/test_sessions_api.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/repositories/work.py packages/core/services/runtime.py packages/harness apps/api/routers apps/api/main.py tests/unit/harness tests/integration/api/test_work_items_api.py tests/integration/api/test_sessions_api.py
git commit -m "feat: add work items and idempotent work sessions"
```

### Task 5: Make MCP the customer-local Repository Observer

**Files:**

- Create: `packages/local_connector/__init__.py`
- Create: `packages/local_connector/git_observer.py`
- Create: `packages/local_connector/sanitization.py`
- Create: `packages/domain/local_workspace.py`
- Modify: `apps/mcp/schemas.py`
- Modify: `apps/mcp/server.py`
- Modify: `apps/mcp/tools.py`
- Modify: `packages/harness/project_resolver.py`
- Test: `tests/unit/local_connector/test_git_observer.py`
- Test: `tests/unit/local_connector/test_sanitization.py`
- Test: `tests/unit/mcp/test_stdio_server.py`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/integration/mcp/test_local_connector_process.py`

- [ ] **Step 1: Write failing local observation and privacy tests**

Create temporary Git repositories with HTTPS credentials, SSH remotes, branches, commits and dirty files. Assert the observation contains normalized host/path identity, branch, head commit and dirty state, but never contains:

```text
absolute repository path
username
password/token
file contents
untracked file contents
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `.venv/bin/pytest tests/unit/local_connector tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py -v`

Expected: FAIL because LocalWorkspaceObservation does not exist.

- [ ] **Step 3: Implement RepositoryIdentity and LocalWorkspaceObservation**

The stdio MCP process reads `AGORA_WORKSPACE_ROOT` or its current working directory, invokes local Git, sanitizes the result, and attaches the observation to `agora_start_work`. The API receives metadata only and must never accept or dereference a local path.

- [ ] **Step 4: Version the Harness protocol and stable errors**

Every canonical response includes `protocol_version`, `request_id`, `capabilities` and a structured next action. Use the canonical errors `PROJECT_UNRESOLVED`, `WORK_ITEM_CLARIFICATION_REQUIRED`, `UNAUTHORIZED_PROJECT`, `PROTOCOL_VERSION_UNSUPPORTED` and `TEMPORARILY_UNAVAILABLE`, plus P2 protocol errors `AUTH_REQUIRED`, `INVALID_CREDENTIAL`, `INVALID_OBSERVATION`, `IDEMPOTENCY_CONFLICT` and `TOKEN_BUDGET_TOO_SMALL`. Legacy adapters map old errors to these codes and include a deprecation marker.

- [ ] **Step 5: Prove the real stdio process privacy boundary**

Launch the actual MCP stdio server from a temporary Git repository, call `agora_start_work`, and capture the real outbound API request with a local HTTP recorder. Assert the request body, MCP result, error output, logs and persisted observation contain no absolute path, Git userinfo/token, tracked source content or untracked source content. This process-level test is required in addition to observer unit tests.

- [ ] **Step 6: Run Connector, MCP and privacy tests**

Run: `.venv/bin/pytest tests/unit/local_connector tests/unit/mcp tests/integration/mcp/test_local_connector_process.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/local_connector packages/domain/local_workspace.py apps/mcp packages/harness/project_resolver.py tests/unit/local_connector tests/unit/mcp tests/integration/mcp/test_local_connector_process.py
git commit -m "feat: observe local repositories through mcp connector"
```

### Task 6: Return multi-dimensional freshness and a fully budgeted ContextBundle

**Files:**

- Create: `packages/harness/context_bundle.py`
- Create: `packages/harness/token_budget.py`
- Modify: `packages/harness/context_planner.py`
- Modify: `packages/harness/service.py`
- Modify: `packages/knowledge/context_engine.py`
- Modify: `packages/domain/schemas.py`
- Test: `tests/unit/harness/test_token_budget.py`
- Test: `tests/unit/harness/test_context_bundle.py`
- Test: `tests/unit/knowledge/test_context_engine.py`
- Test: `tests/integration/api/test_harness_api.py`

- [ ] **Step 1: Write failing deterministic budget and freshness tests**

Assert the complete, stable-JSON-serialized L0/L1 payload stays within the requested estimate, including envelope, facts, constraints, risks, workflow requirements, Skill summaries, diagnostics and source metadata. Assert deterministic trimming order and separate L2 `max_tokens`. Cover the canonical freshness dimensions:

```text
repository_relation: exact | descendant | ancestor | diverged | unknown
workspace_state: clean | dirty | unknown
context_coverage: missing | fresh | potentially_stale | stale | unknown
proposal_state: none
accepted_revision_id: null
observed_commit_sha: string | null
recommended_action: use_provisional_context | analyze_local_project | clarify_repository
```

P2 has no accepted ContextRevision base, so repository relation is normally `unknown`, `accepted_revision_id` is null, and context coverage is `missing` or explicitly provisional through a P2 extension field. It must never claim `fresh`, `exact` or accepted reuse from a legacy ContextPack.

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `.venv/bin/pytest tests/unit/harness/test_token_budget.py tests/unit/harness/test_context_bundle.py tests/integration/api/test_harness_api.py -v`

Expected: FAIL because current token budgeting covers only legacy context selection.

- [ ] **Step 3: Implement the canonical provisional ContextBundle**

Rename the primary operation to `prepare_context`. Wrap existing ContextPack material as `ContextBundle.provisional=true`, preserve source references, and set `recommended_action=analyze_local_project` when no reusable material exists. `provisional` is not added to the canonical `context_coverage` enum. Never claim an accepted ContextRevision in P2.

- [ ] **Step 4: Implement whole-payload token enforcement**

Use stable JSON serialization and one versioned deterministic estimator. Keep protocol envelope and critical constraints; trim optional facts and source metadata before truncating the summary. Return `budget_limit`, `estimated_tokens`, `estimator_version` and truncation diagnostics inside the budgeted payload. Define a minimum viable budget: when the non-trimmable envelope and L0 exceed it, return stable `TOKEN_BUDGET_TOO_SMALL` rather than violating the budget. Validate the final encoded payload after diagnostics are attached. L2 fetch remains a separate command with its own independently tested `max_tokens`.

- [ ] **Step 5: Run focused and integration tests**

Run: `.venv/bin/pytest tests/unit/harness/test_token_budget.py tests/unit/harness/test_context_bundle.py tests/unit/knowledge/test_context_engine.py tests/integration/api/test_harness_api.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/harness packages/knowledge/context_engine.py packages/domain/schemas.py tests/unit/harness tests/unit/knowledge/test_context_engine.py tests/integration/api/test_harness_api.py
git commit -m "feat: prepare budgeted provisional context bundles"
```

---

## Chunk 3: Canonical API, Web Visibility and Full P2 Acceptance

### Task 7: Publish the canonical Harness API and MCP tools

**Files:**

- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/server.py`
- Modify: `apps/mcp/schemas.py`
- Modify: `apps/mcp/tools.py`
- Modify: `tests/integration/api/test_harness_api.py`
- Modify: `tests/unit/mcp/test_stdio_server.py`
- Modify: `tests/unit/mcp/test_tools.py`
- Test: `tests/e2e/test_p2_harness_loop.py`

- [ ] **Step 1: Write a failing protocol-level end-to-end test**

Drive the same public operations used by a real MCP client:

```text
agora_start_work
agora_prepare_context
agora_fetch_context_ref
agora_close_work
```

Verify bearer auth, protocol version, idempotency, project/work resolution, privacy, ContextBundle budget, WorkSession close and audit events.

This is the P2 canonical advertised subset of the architecture's full future tool catalog. `agora_record_event`, `agora_plan_context`, `agora_prepare_writeback` and other P1 operations remain non-advertised compatibility dispatches with deprecation metadata. Document their mapping to canonical errors and their removal target; do not treat them as P2 product tools.

- [ ] **Step 2: Run the E2E test and verify it fails**

Run: `.venv/bin/pytest tests/e2e/test_p2_harness_loop.py -v`

Expected: FAIL because the canonical operation set is not wired end to end.

- [ ] **Step 3: Wire canonical endpoints and compatibility aliases**

Add `/harness/prepare-context`; keep `/harness/plan-context` as a deprecated adapter returning the canonical schema. Advertise only the four-tool P2 subset above, but accept legacy dispatch during P2 for compatibility. Remove `not_implemented` responses from advertised tools; unimplemented P3-P5 capabilities must be absent or explicitly false. Add a protocol compatibility table covering legacy tool names, canonical replacements, error-code mapping, deprecation marker and removal phase.

- [ ] **Step 4: Run API, MCP and E2E tests**

Run: `.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/mcp tests/e2e/test_p2_harness_loop.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/harness.py apps/mcp tests/integration/api/test_harness_api.py tests/unit/mcp tests/e2e/test_p2_harness_loop.py
git commit -m "feat: publish canonical p2 harness protocol"
```

### Task 8: Show WorkItems, WorkSessions and context state in Web

**Files:**

- Create: `apps/web/app/projects/[projectId]/work-items/page.tsx`
- Create: `apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modify: `apps/web/components/Nav.tsx`
- Modify: `apps/web/app/styles.css`
- Test: `tests/integration/api/test_work_items_api.py`
- Test: `tests/integration/test_web_config.py`

- [ ] **Step 1: Add failing API projection assertions for Web data**

Assert WorkItem list/detail provides title, external key, status, participants, WorkSessions, latest context state and nullable capability pins without exposing credentials or local paths.

- [ ] **Step 2: Implement quiet operational Web views**

Add a WorkItems list and detail view. Reuse the established restrained layout; do not rebuild the prototype as a marketing page. Replace the product Context Tester execution form with a read-only ContextBundle and context-state audit view that labels P1 material as provisional. Any retained administrator diagnostic action must be access-controlled, explicitly non-product, absent from normal navigation and excluded from black-box acceptance. Session pages link back to their WorkItem.

- [ ] **Step 3: Build and inspect desktop/mobile rendering**

Run: `cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build`

Expected: PASS with no route/type errors.

Use browser validation at desktop and 390×844 widths. Expected: no unstyled page, overlap, horizontal overflow, leaked token or leaked local path.

- [ ] **Step 4: Commit**

```bash
git add apps/web tests/integration/api/test_work_items_api.py tests/integration/test_web_config.py
git commit -m "feat: expose p2 work state in web"
```

### Task 9: Prepare and verify the complete real-AI-tool P2 black-box

**Files:**

- Create: `scripts/prepare_p2_blackbox.py`
- Create: `docs/development/p2-real-ai-tool-blackbox.zh-CN.md`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Test: `tests/integration/test_p2_blackbox_setup.py`
- Test: `tests/integration/test_p2_postgres.py`

- [ ] **Step 1: Write a failing setup test**

The setup command must idempotently prepare:

- A realistic Chinese software R&D repository such as a payment service with issue `PAY-241`, source, tests and architecture notes.
- Local human and agent tokens supplied through environment variables.
- A Project whose sanitized repository identity matches the temporary repository.
- No precomputed AI context, Fake LLM result or fake AI-tool response.

- [ ] **Step 2: Implement the idempotent black-box preparation command**

The command may create local test data and configuration, but it must use the same project, auth and migration paths as production code. It must not call hidden test APIs or insert a successful Harness result directly.

- [ ] **Step 3: Run the complete automated verification**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: all Python tests and Web build pass.

- [ ] **Step 4: Run migration rehearsal against a copy of the current local database**

Back up `.agora/agora.db`, upgrade the copy to Alembic head, compare table counts and verify existing projects/assets/sessions/writebacks/skills remain queryable. Never run destructive downgrade against the user's live database.

- [ ] **Step 5: Verify Postgres transaction and concurrency semantics**

Start the existing `infra/docker-compose.yml` Postgres service and run the P2 migrations plus dedicated tests against it. Prove Unit of Work rollback after flush, concurrent idempotency-key conflict/replay, uniqueness enforcement and membership isolation under Postgres. SQLite remains supported locally, but it cannot be the only team acceptance database.

Run:

```bash
docker compose -f infra/docker-compose.yml up -d postgres
AGORA_TEST_POSTGRES_URL=postgresql+psycopg://agora:agora@127.0.0.1:5432/agora .venv/bin/pytest tests/integration/test_p2_postgres.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the real AI-tool and Web black-box internally**

Start API and Web against Postgres with authentication enabled, configure the actual AI tool to use Agora MCP, open the prepared repository, and issue a realistic software task. The evidence checklist must prove every P2 exit condition:

- AI tool resolves Project and WorkItem without manual selection when repository identity is unambiguous.
- Start response contains authenticated Principal-derived ownership, one idempotent WorkSession, nullable version pins and false P3-P5 capability flags.
- Repeating start with the same key replays the same response; changing payload with the key returns `IDEMPOTENCY_CONFLICT`.
- `agora_prepare_context` returns canonical freshness dimensions and either an explicitly provisional bundle or `analyze_local_project`.
- The real AI tool follows `analyze_local_project` by reading the local repository itself; Agora server never reads the path.
- Final serialized L0/L1 stays within budget and `agora_fetch_context_ref` enforces its independent L2 limit.
- `agora_close_work` closes the same WorkSession without duplicate state.
- Captured MCP traffic, API logs and persisted observations contain no absolute path, Git credentials or source content from the start request.
- Web shows the same WorkItem, WorkSession, context state and audit events without manual API use.

- [ ] **Step 7: Record internal evidence and prepare user black-box**

Record implementation commits, test counts, Web build, SQLite migration rehearsal, Postgres semantics, browser checks, service URLs and the exact user black-box path. Set P2 to `Awaiting user black-box`, not complete.

- [ ] **Step 8: Commit internal acceptance evidence**

```bash
git add scripts/prepare_p2_blackbox.py docs README.md tests/integration/test_p2_blackbox_setup.py tests/integration/test_p2_postgres.py
git commit -m "docs: prepare p2 real ai tool acceptance"
```

- [ ] **Step 9: Record the user's real black-box decision**

After the user runs the documented AI-tool and Web steps, append the date, actual observations and pass/fail decision to the roadmap execution log. Only a user-confirmed pass changes P2 status to `Complete`; a failure keeps P2 active and becomes the next implementation task. Commit the decision separately so the historical gate is auditable.

---

## Final P2 Definition of Done

- Existing P1 database content survives an additive migration and remains visible.
- A real AI tool invokes Agora through authenticated MCP without sending a local absolute path or source content in the start request.
- Agora resolves Project and WorkItem, creates one idempotent WorkSession and returns structured next actions.
- Existing context is clearly provisional; missing/stale context asks the real AI tool to analyze locally.
- The full serialized L0/L1 ContextBundle obeys its budget; L2 source expansion is separately limited.
- Human and agent credentials are distinct, project membership is enforced, and tenant identity is not trusted from payloads.
- One failed Harness command cannot leave partial state.
- All Python tests pass, Next.js builds, Postgres transaction/concurrency checks pass, desktop/mobile Web checks pass, and the full real AI-tool black-box path passes internally.
- The user confirms the documented real AI-tool and Web black-box passed; until then P2 remains `Awaiting user black-box`.
- The roadmap execution log contains implementation, test and black-box evidence.
