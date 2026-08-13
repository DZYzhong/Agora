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

### 2026-08-13: P4 Skill Lifecycle Started

Scope:

- Started P4 Skill Lifecycle.
- Created a durable implementation plan for Skill CRUD, approval/deprecation workflow, SkillRun history, and Web lifecycle controls.
- P4 will be developed as a larger validation batch instead of requiring user validation after each small field or endpoint.

Files changed:

- Created: `docs/superpowers/plans/2026-08-13-agora-p4-skill-lifecycle.md`

Verification:

- Not run for plan-only change.

Commit:

- `feat: audit skill lifecycle failures`

### 2026-08-13: P4 Candidate Skills from Accepted Writebacks

Scope:

- Added candidate skill creation from repeated accepted writebacks.
- When two or more accepted writebacks of the same project/type exist, Agora creates one candidate project skill.
- Candidate skill definitions include source metadata, writeback type, triggers, input schema, instructions, and evidence writeback IDs.
- This connects repeated AI memory/writeback patterns to reviewable team workflow assets.

Files changed:

- Modified: `packages/core/repositories/writebacks.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/memory_writeback.py`
- Modified: `tests/integration/api/test_skills_api.py`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p4-skill-lifecycle.md`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_skills_api.py::test_repeated_accepted_writebacks_create_candidate_skill -v
# 1 passed

.venv/bin/pytest tests/integration/api/test_skills_api.py -v
# 2 passed

.venv/bin/pytest -q
# 60 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Prepare and accept two writebacks of the same type.
- Open the project's Skills page.
- Expected: a candidate project skill appears with slug derived from the writeback type.

Black-box validation:

- User confirmed the grouped P4 validation passed.
- The Skills page showed the auto-created candidate from repeated accepted writebacks.

Commit:

- `feat: create candidate skills from writebacks`

### 2026-08-13: P4 Skill Lifecycle API and Web

Scope:

- Added project-scoped Skill lifecycle API.
- Skills can now be created, edited, approved, deprecated, run, and listed with run history.
- Built-in skills are lazily seeded and listed alongside project skills.
- SkillRun records persist input, output, warnings, status, session ID, and timestamps.
- Replaced the static Skills page with a lifecycle management UI: create candidate, edit definition, approve/deprecate, run skill, and inspect run history.

Files changed:

- Created: `packages/core/repositories/skills.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/skill_orchestrator.py`
- Created: `apps/api/routers/skills.py`
- Modified: `apps/api/main.py`
- Modified: `apps/web/lib/api.ts`
- Modified: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Created: `apps/web/app/projects/[projectId]/skills/create/route.ts`
- Created: `apps/web/app/projects/[projectId]/skills/[skillId]/update/route.ts`
- Created: `apps/web/app/projects/[projectId]/skills/[skillId]/approve/route.ts`
- Created: `apps/web/app/projects/[projectId]/skills/[skillId]/deprecate/route.ts`
- Created: `apps/web/app/projects/[projectId]/skills/[skillId]/run/route.ts`
- Modified: `apps/web/app/styles.css`
- Created: `tests/integration/api/test_skills_api.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_skills_api.py -v
# 1 passed

.venv/bin/pytest -q
# 59 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project's Skills page.
- Expected: built-in approved skills are listed.
- Create a candidate project skill.
- Edit it to draft, approve it, run it, inspect Skill runs, then deprecate it.

Black-box validation:

- User confirmed the grouped P4 validation passed.
- The Skills page showed built-in approved skills, a manual candidate skill, and an auto-generated candidate skill.
- User validated editing, approving, running, run-history visibility, and deprecating a project skill.

Commit:

- `feat: add skill lifecycle management`

### 2026-08-13: P4 Skill Run Audit and Built-in Guardrails

Scope:

- Failed skill runs are now persisted as `SkillRun` rows with `status=failed`, error output, warnings, input, skill ID, project ID, and timestamp.
- Deprecated or otherwise unapproved skill run attempts remain blocked, but the failed attempt is visible in run history.
- Built-in skills are read-only for lifecycle mutations: update, approve, and deprecate reject built-ins instead of mutating shared/global behavior.
- The Skills page hides approve/deprecate controls for built-in skills.
- The Skills page run action redirects back to run history after a blocked run so the persisted failed record is visible.

Files changed:

- Modified: `apps/api/routers/skills.py`
- Modified: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Modified: `apps/web/app/projects/[projectId]/skills/[skillId]/run/route.ts`
- Modified: `tests/integration/api/test_skills_api.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_skills_api.py -v
# 3 passed

.venv/bin/pytest -q
# 61 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project's Skills page.
- Expected: built-in skills show no approve/deprecate buttons.
- Run an approved project skill and confirm a completed run appears.
- Deprecate that same project skill, run it again, and confirm the page returns to Skill runs with a failed run entry containing the error.

Commit:

- `feat: audit skill lifecycle failures`

### 2026-08-13: P4 Candidate Skill Evidence Review

Scope:

- Candidate skills generated from accepted writebacks now expose `evidence_refs` in the Skills API.
- Evidence refs include writeback ID, type, title, status, accepted asset ID, and a compact content preview.
- The Skills page renders an Evidence section on skill cards, so reviewers can inspect why an auto-generated candidate exists before approving it.
- Added repository/runtime helpers to load writebacks by ordered evidence IDs.

Files changed:

- Modified: `packages/core/repositories/writebacks.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `apps/api/routers/skills.py`
- Modified: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Modified: `apps/web/app/styles.css`
- Modified: `tests/integration/api/test_skills_api.py`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p4-skill-lifecycle.md`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_skills_api.py::test_repeated_accepted_writebacks_create_candidate_skill -v
# 1 passed
```

Black-box validation path:

- Create or open a project with two accepted writebacks of the same type.
- Open the project's Skills page.
- Expected: the auto-generated candidate skill shows an Evidence section with both writeback titles and previews.
- Approve the candidate and confirm the Evidence section remains visible for audit context.

Black-box validation:

- User confirmed the P4 candidate evidence validation passed.
- The Skills page showed the candidate skill evidence section with both accepted writeback titles and previews.
- The evidence section remained visible after approving the candidate skill.

Commit:

- `feat: show candidate skill evidence`

### 2026-08-13: P5 Session Audit Started

Scope:

- Started P5 Session Memory and Work Audit with a larger implementation batch.
- Created a durable P5 implementation plan covering session filters, detail audit API, Web list filters, Web detail page, and black-box fixture validation.
- Added session list filtering by intent, status, and audit-content search query.
- Added a project-scoped session detail API endpoint.
- Session audit payloads now include context packs, skill runs, writebacks, events, and audit counters.
- Added Web session filters, audit counters, and detail links.
- Added a Web session audit detail page showing context packs, source refs, skill runs, writebacks, and event timeline.

Files changed:

- Created: `docs/superpowers/plans/2026-08-13-agora-p5-session-audit.md`
- Modified: `packages/core/repositories/sessions.py`
- Modified: `packages/core/repositories/skills.py`
- Modified: `packages/core/repositories/writebacks.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `apps/api/routers/sessions.py`
- Modified: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Created: `apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx`
- Modified: `apps/web/app/styles.css`
- Created: `tests/integration/api/test_sessions_api.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_sessions_api.py tests/integration/api/test_harness_api.py tests/integration/api/test_skills_api.py -v
# 9 passed

.venv/bin/pytest -q
# 62 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with multiple sessions.
- Use the Sessions page filters for intent/status/search.
- Open a session audit detail page.
- Expected: the detail page shows audit counters, context packs, source refs, skill runs, writebacks, and timeline events.

Black-box validation:

- User confirmed the P5 Session Audit validation passed.
- Sessions filtering, audit counters, and the session detail page were verified from the browser.
- Future black-box fixtures should use China-oriented software R&D team data by default, including requirements, iterations, defects, code review, regression testing, release risk, gray releases, monitoring alerts, incident review, CI/CD, and engineering collaboration scenarios.

Commit:

- `feat: add session audit workspace`

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

- `feat: fetch context source references`

Black-box validation:

- User confirmed the Context Tester source reference flow passed.
- Clicking `View source` opened a source detail page with traceable source content.

### 2026-08-13: P3 Source Reference Previews

Scope:

- Added short `preview` text to ContextPack source references.
- Context Tester now displays source preview text inline before the `View source` link.
- This makes source relevance easier to judge before opening the full source detail page.

Files changed:

- Modified: `packages/knowledge/context_engine.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`
- Modified: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modified: `apps/web/app/styles.css`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py -v
# 4 passed

.venv/bin/pytest -q
# 52 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with assets.
- Go to Context and run a query.
- Expected: each source row shows a short preview of matched source content plus `View source`.

Commit:

- `feat: preview context source references`

Black-box validation:

- User confirmed the Context Tester preview flow passed.
- Source rows displayed preview text before opening full source detail.

### 2026-08-13: P3 Source Reference Chunk Spans

Scope:

- Added stable `chunk_id` values to ContextPack source references.
- Added `source_span` metadata with line and character ranges for each source reference.
- Context Tester now displays chunk ID and line range in each source row.
- This is currently asset-level tracing (`chunk:0`) and prepares the surface for later asset-type chunking.

Files changed:

- Modified: `packages/knowledge/context_engine.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`
- Modified: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modified: `apps/web/app/styles.css`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_generates_traceable_context_pack -v
# 1 passed

.venv/bin/pytest -q
# 52 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with initialized assets.
- Go to Context and run a query.
- Expected: each source row shows a stable chunk ID like `<asset_id>:chunk:0` and a line range like `lines 1-12`.
- Click `View source`.
- Expected: the full source detail page still opens normally.

Commit:

- `feat: add context source spans`

Black-box validation:

- User confirmed this flow passed.
- Context Tester source rows displayed stable chunk IDs and line ranges.
- `View source` continued to open the full traceable source detail page.

### 2026-08-13: P3 Intent-Aware Retrieval Boosts

Scope:

- Added `asset_type` to fake keyword/vector search results and merged search candidates.
- ContextEngine now re-ranks retrieved candidates by intent.
- Implementation work boosts code files; risk/review work boosts accepted writebacks and analysis memory; docs work boosts docs and project overview assets.
- Context Tester now displays asset type beside retrieval source labels.

Files changed:

- Modified: `packages/knowledge/context_engine.py`
- Modified: `packages/knowledge/retrieval.py`
- Modified: `packages/storage/opensearch/fake.py`
- Modified: `packages/storage/qdrant/fake.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`
- Modified: `apps/web/app/projects/[projectId]/context/page.tsx`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_boosts_sources_by_intent -v
# 1 passed

.venv/bin/pytest tests/unit/knowledge/test_context_engine.py tests/unit/knowledge/test_indexing.py -v
# 7 passed

.venv/bin/pytest -q
# 53 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with initialized assets.
- Go to Context and run a code-oriented query, such as a class, module, or implementation keyword.
- Expected: source rows show asset type labels like `code_file`, `doc`, `writeback`; implementation-oriented results should favor relevant `code_file` rows when scores are close.
- Run a risk-oriented query, such as `风险 一致性 Kafka retry`.
- Expected: accepted writeback or analysis-style context should rank higher when it matches the query.

Commit:

- `feat: rank context sources by intent`

Black-box validation:

- User confirmed this flow passed.
- Implementation query ranked `code_file` first in the prepared fixture project.
- Risk-oriented query ranked `writeback` first in the prepared fixture project.

### 2026-08-13: P3 Matching Chunk Source References

Scope:

- Upgraded ContextPack source references from asset-level `chunk:0` spans to query-matched chunk spans.
- Added source chunk selection inside ContextEngine using paragraph chunks and query token overlap.
- Source refs now point to the best matching paragraph chunk, with stable `chunk_id`, line range, character range, and preview from that chunk.
- Kept API/Web field shape unchanged, so existing Context Tester and source detail flows continue to work.

Files changed:

- Modified: `packages/knowledge/context_engine.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_source_ref_points_to_matching_chunk -v
# 1 passed

.venv/bin/pytest tests/unit/knowledge/test_context_engine.py -v
# 6 passed

.venv/bin/pytest -q
# 54 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a project with initialized assets containing multi-paragraph docs/code.
- Go to Context and query a term that appears in a later paragraph.
- Expected: source row preview shows the matching paragraph rather than the first paragraph.
- Expected: source row line range points to the matched paragraph, such as `lines 3-3`, with a matching `chunk:<n>` value.

Commit:

- `feat: match context refs to chunks`

Black-box validation:

- User confirmed this flow passed.
- Querying `refund idempotency` in the prepared chunk fixture showed the matching later paragraph.
- The source row displayed a later `chunk:<n>` value and matching later line range instead of always using `chunk:0`.

### 2026-08-13: P3 Context Levels and Chunk Facts

Scope:

- Added semantic ContextPack levels: `overview`, `module`, `source`, `memory`, and `empty`.
- Updated key facts to reference stable chunk IDs instead of raw asset IDs.
- Context Tester now displays Context level and Key facts.
- `View source` links now carry `chunk_id`, `start_line`, and `end_line` to the source detail page.
- Context Source detail page displays which chunk/line range opened the full source.

Files changed:

- Modified: `packages/knowledge/context_engine.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`
- Modified: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modified: `apps/web/app/projects/[projectId]/context/source/[assetId]/page.tsx`
- Modified: `apps/web/app/styles.css`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py -v
# 6 passed

.venv/bin/pytest -q
# 54 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open Context Tester for a project and run a query.
- Expected: Session panel shows `Context level: ...`.
- Expected: Key facts panel appears and each fact references a chunk ID.
- Expected: Source rows still show preview, chunk ID, line range, asset type, retrieval source, and score.
- Click `View source`.
- Expected: Source detail page shows `Opened from <chunk_id> · lines <start>-<end>` above the full content.

Commit:

- `feat: expose context levels and chunk facts`

### 2026-08-13: P3 Retrieval Evaluation Fixture

Scope:

- Added a focused retrieval evaluation test covering overview, source, memory, and chunk-fact behavior together.
- The fixture indexes project overview, code, writeback memory, and docs into the fake keyword/vector indexes.
- This locks in the intended P3 behavior across broad project queries, implementation queries, review/risk queries, and chunk-level fact references.

Files changed:

- Created: `tests/unit/knowledge/test_context_retrieval_eval.py`

Verification:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_retrieval_eval.py -v
# 1 passed

.venv/bin/pytest -q
# 55 passed

cd apps/web && npm run build
# passed
```

Black-box validation:

- Covered together with the P3 Context Levels and Chunk Facts validation flow.

Commit:

- `test: add context retrieval evaluation`

### 2026-08-13: P3 Overview Query Intent Fix

Scope:

- Fixed project overview requests such as `介绍一下这个项目` being misclassified as `implementation`.
- Added analysis intent inference for English overview/summarize/analyze requests and Chinese introduction/overview/core-module/business-flow requests.
- Added regression coverage proving broad overview queries prefer `Project Overview` even when docs/code files also match query terms.

Files changed:

- Modified: `packages/harness/task_resolver.py`
- Modified: `tests/unit/harness/test_harness_service.py`
- Modified: `tests/unit/knowledge/test_context_engine.py`

Verification:

```bash
.venv/bin/pytest tests/unit/harness/test_harness_service.py::test_start_work_infers_analysis_intent_for_project_overview_request tests/unit/knowledge/test_context_engine.py::test_context_engine_prefers_project_overview_for_broad_query_even_with_matching_files -v
# 2 passed

.venv/bin/pytest tests/unit/harness/test_harness_service.py tests/unit/knowledge/test_context_engine.py tests/unit/knowledge/test_context_retrieval_eval.py -v
# 13 passed

.venv/bin/pytest -q
# 57 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Re-open the project overview query URL.
- Expected: Session intent shows `analysis`, Context level shows `overview`, and Project Overview ranks first.

Commit:

- `fix: infer analysis intent for overview queries`

Black-box validation:

- User confirmed the grouped P3 validation passed.
- Overview query now shows `analysis`, `Context level: overview`, and Project Overview ranks first.

### 2026-08-13: P3 Persisted ContextPack Session Timeline

Scope:

- Persisted every planned ContextPack into the `context_packs` table.
- Recorded a `context_planned` session event containing ContextPack ID, level, and source count.
- Extended the sessions API to return ContextPack history attached to each session.
- Sessions page now shows ContextPack level, summary, key facts, and source count for each session.
- This completes the P3 audit loop: a reviewer can see what context was generated for a session after the fact.

Files changed:

- Created: `packages/core/repositories/context_packs.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/context_planner.py`
- Modified: `apps/api/routers/sessions.py`
- Modified: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Modified: `apps/web/app/styles.css`
- Modified: `tests/integration/api/test_harness_api.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_plan_context_persists_context_pack_on_session_timeline -v
# 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/harness/test_harness_service.py -v
# 10 passed

.venv/bin/pytest -q
# 58 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Run one or more Context Tester queries for a project.
- Open that project's Sessions page.
- Expected: the latest sessions show ContextPack blocks with level, summary, key facts, and source count.
- Expected: session events include `context_planned` with the ContextPack ID.

Commit:

- `feat: persist context packs on sessions`

Black-box validation:

- User confirmed the grouped P3 validation passed.
- Sessions page showed generated ContextPack history, including level, summary, key facts, source count, and `context_planned` events.
