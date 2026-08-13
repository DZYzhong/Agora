# Agora P1-P9 Roadmap and Execution Log

> **Purpose:** This file is the durable roadmap and recovery log for Agora after chat history loss. When work is completed, update this document with what changed, which commit was created, and which verification commands passed or failed.

**Current branch:** `codex/agora-p0`

**Current baseline:** P0 is implemented. P1 local team trial is implemented. The next recommended phase is P2.

**Log rule:** Every implementation task should append an entry under "Execution Log" before the final response. Include date, scope, files changed, commit SHA if available, and exact verification commands/results.

---

## Current Implementation Snapshot

As of 2026-08-13, the codebase is a local team-trial build:

- FastAPI backend with SQLAlchemy repositories.
- SQLite file database by default at `.agora/agora.db`.
- In-memory fake keyword/vector indexes, rebuilt from persisted assets on API startup.
- Project creation, listing, initialization, initialization job tracking, and archiving.
- Git local repository analysis with fallback clone from the first configured remote.
- Asset normalization for repository knowledge, including generated project overview assets.
- ContextPack planning through fake keyword/vector retrieval.
- Harness work lifecycle: start work, plan context, record events, close work.
- Development update capture from agent summaries, tests, and optional git diffs.
- Writeback draft, accept/reject review, accepted writeback re-indexing.
- Stdio MCP adapter for agent calls.
- Minimal Next.js admin UI for projects, assets, skills, sessions, context testing, and writeback review.

Known limits:

- No production auth, user model, org membership, or RBAC.
- No Alembic migration workflow yet.
- No real Qdrant/OpenSearch/Neo4j adapters wired into runtime.
- No background job queue or real Temporal worker.
- No robust Git credential management, scheduled sync, or incremental sync.
- MCP `agora_fetch_context_ref` is still a shallow placeholder in the local tool class.
- External task systems, docs systems, PR metadata, and CI integrations are not implemented.

Baseline verification:

```bash
.venv/bin/pytest -q
# 42 passed
```

---

## P1: Local Team Trial

**Goal:** Move Agora from P0 demo into a local team-trial build where project data survives restarts, initialization is trackable, and AI tools can reuse project context.

**Status:** Complete.

Delivered:

- File SQLite persistence with `AGORA_DATABASE_URL`.
- Rehydration of in-memory fake search indexes from persisted assets.
- Project initialization job model and API.
- Web initialization status and error display.
- Generated project overview asset.
- Web context tester.
- Web accept/reject writeback review.
- Development update capture on close work.
- Accepted writeback retrieval priority.
- Project archiving.

Reference plan:

- `docs/superpowers/plans/2026-08-11-agora-p1-team-trial.md`

---

## P2: Real Repository Trial Hardening

**Goal:** Make Agora reliable enough to trial against real team repositories, not only sample fixtures.

Recommended scope:

- Add explicit repository source records for local paths and remotes.
- Support re-initializing a project without blindly duplicating assets.
- Add content hash based upsert/update behavior for ingested assets.
- Add incremental re-sync for changed files where feasible.
- Improve ignore rules for `.git`, dependencies, build output, binary files, large files, and hidden local artifacts.
- Persist initialization diagnostics: scanned file count, skipped file count, warnings, and failure reason.
- Add retry/re-run semantics for failed initialization jobs.
- Expose initialization history and re-run actions in Web.
- Add tests using a richer fixture repository with nested packages and ignored files.

Exit criteria:

- A project can be initialized, re-initialized, and queried without duplicate knowledge pollution.
- A failed initialization can be inspected and retried.
- Large/generated/binary files are skipped deterministically.
- Full Python tests and Web build pass.

---

## P3: Context Quality Upgrade

**Goal:** Make agent context more precise, traceable, and useful for implementation/review work.

Recommended scope:

- Implement real `agora_fetch_context_ref`.
- Add stable chunk IDs and source spans.
- Improve chunking by asset type.
- Add ContextPack levels, such as project overview, module detail, source snippets, and accepted writebacks.
- Add intent-aware retrieval boosts for implementation, review, testing, docs, and risk work.
- Include richer source references with asset ID, source URI, chunk ID, and preview.
- Add retrieval evaluation fixtures.

Exit criteria:

- Agents can fetch full source refs from ContextPack output.
- Broad queries prefer overview assets; specific queries prefer source/writeback details.
- Retrieval tests cover broad, specific, and accepted-writeback cases.

---

## P4: Skill Lifecycle

**Goal:** Turn built-in skills into reviewable, versioned team workflow assets.

Recommended scope:

- Add Skill CRUD APIs.
- Support candidate, draft, approved, and deprecated skill states.
- Persist skill definitions with input schema, triggers, instructions, and version metadata.
- Add Web pages for skill review and approval.
- Record SkillRun input, output, status, warnings, and errors.
- Add candidate skill creation from repeated accepted writebacks.

Exit criteria:

- A team can create, edit, approve, run, and inspect a skill through API/Web.
- SkillRun history is visible and test-covered.

---

## P5: Session Memory and Work Audit

**Goal:** Make each AI work session auditable and reusable as project memory.

Recommended scope:

- Add a richer session timeline in Web.
- Standardize event types for context planned, skill run, file changed, tests run, writeback drafted, and close work.
- Structure development update content into summary, files changed, tests, risks, and follow-ups.
- Link sessions to accepted writebacks and created assets.
- Add session search/filter by project, intent, status, and date.

Exit criteria:

- A reviewer can open a session and understand what context was used, what the agent did, what tests ran, and what knowledge was produced.

---

## P6: Production Persistence Baseline

**Goal:** Prepare persistence and indexes for a production-like deployment path.

Recommended scope:

- Introduce Alembic migrations.
- Add Postgres runtime configuration.
- Add repository tests that run against SQLite and optionally Postgres.
- Implement initial Qdrant and OpenSearch adapters behind current fake interfaces.
- Add index rebuild CLI/script.
- Add safe reset/rebuild commands for local development.
- Decide whether Neo4j remains deferred or gets a minimal adapter.

Exit criteria:

- Database schema changes are migration-managed.
- Runtime can use Postgres and real search adapters behind config flags.
- Local fake mode remains fast and testable.

---

## P7: Team Governance and Access

**Goal:** Add basic team boundaries and control surfaces needed before broader use.

Recommended scope:

- Add User, Organization, Membership, and ProjectMembership models.
- Add API authentication boundary.
- Add simple role model for admin, maintainer, reviewer, and viewer.
- Restrict writeback approval and project archive/delete operations by role.
- Add audit log entries for sensitive actions.
- Add Web affordances for current user/org/project role.

Exit criteria:

- Project access is scoped by org and membership.
- Review and archive actions are auditable.

---

## P8: Integrations

**Goal:** Connect Agora to real team workflow surfaces.

Recommended scope:

- GitHub/GitLab PR metadata ingestion.
- Task system integration, starting with a mock adapter and then Linear/Jira-style adapters.
- Docs ingestion for Markdown directories or external docs exports.
- OpenAPI ingestion for service/API context.
- CI/test result import.
- Project resolution from task URL, PR URL, branch name, or repository remote.

Exit criteria:

- An agent can start from a task/PR reference and get project-specific context without manual project selection.

---

## P9: Hosted Beta and Ops Readiness

**Goal:** Make Agora practical to run for a small team over time.

Recommended scope:

- Dockerized deploy path for API, Web, database, and index services.
- Health/readiness endpoints.
- Structured logging and request IDs.
- Backup/restore documentation for database and indexes.
- Admin scripts for reindex, reset, data export, and diagnostics.
- Smoke test script for deployed environments.
- Upgrade path documentation.

Exit criteria:

- A small team can deploy Agora, onboard a repository, run agent workflows, review writebacks, and recover from common operational issues.

---

## Execution Log

### 2026-08-13: Roadmap Reconstructed

Scope:

- Reconstructed the P1-P9 roadmap after chat history loss.
- Scanned local Markdown files and confirmed only P0 and P1 plan files existed.
- Scanned current code structure and recent commits to summarize implementation state.
- Created this durable roadmap and execution log file.

Files changed:

- Created: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest -q
# 42 passed
```

Notes:

- P1 is treated as complete based on the existing P1 plan and current passing tests.
- P2 is the recommended next implementation phase.

### 2026-08-13: P2 Repository Initialization Hardening Started

Scope:

- Created a detailed P2 implementation plan.
- Added idempotent asset upsert by `project_id + source_uri`.
- Changed project initialization to upsert ingested assets instead of always creating new rows.
- Added content hashes for file assets and generated project overview assets.
- Added repository analyzer diagnostics for scanned files, skipped files, and warnings.
- Added skip handling for ignored paths, unsupported extensions, large files, and non-UTF-8 text.
- Propagated analyzer warnings through `InitializeProjectResult` and initialization job completion.

Files changed:

- Created: `docs/superpowers/plans/2026-08-13-agora-p2-real-repository-hardening.md`
- Modified: `apps/api/routers/projects.py`
- Modified: `apps/workers/workflows/initialize_project.py`
- Modified: `packages/core/repositories/assets.py`
- Modified: `packages/integrations/git/analyzer.py`
- Modified: `packages/knowledge/ingestion.py`
- Modified: `packages/knowledge/project_overview.py`
- Modified: `tests/integration/api/test_initialization_jobs.py`
- Modified: `tests/integration/workers/test_initialize_project.py`
- Modified: `tests/unit/core/test_repositories.py`
- Modified: `tests/unit/integrations/test_git_analyzer.py`

Verification:

```bash
.venv/bin/pytest tests/unit/core/test_repositories.py -v
# 4 passed

.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
# 3 passed

.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
# 5 passed

.venv/bin/pytest -q
# 46 passed

cd apps/web && npm run build
# passed
```

Commit:

- `feat: harden repository initialization`

### 2026-08-13: P2 Black-Box Feedback Follow-Up

Scope:

- User verified P2 through the project detail page on the persisted `东风大数据` project.
- The core idempotency behavior held: re-initializing `/Users/daniel/Documents/PTest3` completed with 319 assets instead of duplicating to a larger count.
- Black-box review exposed that `.git` files were shown as hundreds of skipped files, which was technically explainable but poor UX and misleading.
- Changed repository scanning to prune ignored directories before file scanning.
- Warnings now summarize ignored directories, such as `.git` and `node_modules`, instead of listing/counting every file inside them.

Files changed:

- Modified: `packages/integrations/git/analyzer.py`
- Modified: `tests/unit/integrations/test_git_analyzer.py`
- Modified: `tests/integration/workers/test_initialize_project.py`
- Modified: `apps/web/app/projects/[projectId]/page.tsx`
- Modified: `apps/web/app/styles.css`

Verification:

```bash
.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
# 6 passed

.venv/bin/pytest -q
# 47 passed

cd apps/web && npm run build
# passed
```

Commit:

- `fix: summarize ignored repository directories`

### 2026-08-13: P2 Warning Noise Reduction

Scope:

- User re-ran black-box validation and confirmed assets remained stable at 319.
- The warning panel was still too noisy because ordinary unsupported files, such as `.gitignore` and shell scripts, were shown as skipped warnings.
- Changed analyzer behavior so unsupported extensions are silently ignored rather than reported as warnings.
- Kept warnings for ignored directories, large supported files, and non-UTF-8 supported source files.

Files changed:

- Modified: `packages/integrations/git/analyzer.py`
- Modified: `tests/unit/integrations/test_git_analyzer.py`

Verification:

```bash
.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
# 7 passed

.venv/bin/pytest -q
# 48 passed

cd apps/web && npm run build
# passed
```

Commit:

- `fix: reduce repository warning noise`

Black-box validation:

- User confirmed the warning noise reduction and repeated initialization behavior passed on the `东风大数据` project.
- Latest repeated initialization stayed at 319 assets and did not duplicate project knowledge.

### 2026-08-13: P2 Failed Initialization Retry

Scope:

- Added API support to retry a failed initialization job using the failed job's original repository path.
- Retry creates a new initialization job, preserving the failed job in history.
- Added Web retry action for failed initialization jobs in the project detail initialization history.
- Retry success revalidates project detail and assets pages.

Files changed:

- Modified: `apps/api/routers/projects.py`
- Modified: `packages/core/repositories/initialization_jobs.py`
- Modified: `tests/integration/api/test_initialization_jobs.py`
- Modified: `apps/web/app/projects/[projectId]/page.tsx`
- Modified: `apps/web/app/styles.css`
- Created: `apps/web/app/projects/[projectId]/initialization-jobs/[jobId]/retry/route.ts`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
# 4 passed

.venv/bin/pytest -q
# 49 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Create or use a project with a failed initialization job.
- Fix the repository path problem outside Agora.
- Open the project detail page and click `Retry` on the failed history row.
- Expected: a new completed job appears above the failed job; assets are created or updated without duplicating existing assets.

Commit:

- `feat: retry failed project initialization`

### 2026-08-13: P2 Stale Asset Pruning

Scope:

- Added pruning for initialization-managed assets that disappear from the repository on re-initialization.
- Pruning applies only to git-ingested assets and the generated project overview asset.
- Agent/manual/writeback assets are not pruned by repository initialization.
- This closes the remaining duplicate/stale knowledge pollution case for moved or deleted files.

Files changed:

- Modified: `apps/api/routers/projects.py`
- Modified: `packages/core/repositories/assets.py`
- Modified: `tests/integration/api/test_initialization_jobs.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py::test_reinitialize_prunes_git_assets_removed_from_repository -v
# 1 passed

.venv/bin/pytest -q
# 50 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Create or use a temporary project initialized from a temporary repository.
- Confirm `src/removed.py` appears in Assets after the first initialization.
- Delete `src/removed.py` from the repository and initialize again.
- Expected: `src/removed.py` no longer appears in Assets; remaining assets are stable and not duplicated.

Black-box validation:

- User confirmed this flow passed with prepared temporary repositories.

Commit:

- `feat: prune stale repository assets`

### 2026-08-13: P3 Context Source Reference Fetch

Scope:

- Started P3 Context Quality work.
- Added backend support for fetching a traceable source reference by `session_id` and `asset_id`.
- Added `POST /harness/fetch-context-ref`.
- Updated MCP stdio tool schema and local MCP adapter so `agora_fetch_context_ref` returns real asset content instead of placeholder content.
- Added Web context source detail page.
- Context Tester source rows now link to source detail when a session is available.

Files changed:

- Created: `docs/superpowers/plans/2026-08-13-agora-p3-context-quality.md`
- Modified: `apps/api/routers/harness.py`
- Modified: `packages/harness/service.py`
- Modified: `apps/mcp/server.py`
- Modified: `apps/mcp/tools.py`
- Modified: `apps/web/app/projects/[projectId]/context/page.tsx`
- Created: `apps/web/app/projects/[projectId]/context/source/[assetId]/page.tsx`
- Modified: `apps/web/app/styles.css`
- Modified: `tests/integration/api/test_harness_api.py`
- Modified: `tests/unit/mcp/test_tools.py`
- Modified: `tests/unit/mcp/test_stdio_server.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_fetch_context_ref_returns_traceable_asset_content -v
# 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py -v
# 4 passed

.venv/bin/pytest -q
# 52 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with assets.
- Go to Context.
- Run a context query that returns source refs.
- Click `View source` on a source row.
- Expected: a source detail page opens showing title, source URI, asset ID, and source content.

Commit:

- Pending.
