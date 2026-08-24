# Agora P1-P9 Roadmap and Execution Log

> **Purpose:** This is Agora's durable implementation roadmap and recovery log. It must be sufficient to recover product direction, completed work and verification evidence after chat history is lost.

**Current branch:** `codex/agora-p0`

**Current baseline:** P0 and the original P1 local trial are implemented. Their code remains a useful foundation, but P2-P9 have been realigned to the Agent-first, Harness-first product design. The next phase is the realigned P2.

**Canonical product design:** `docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`

**Canonical technical architecture:** `docs/superpowers/specs/2026-08-14-agora-technical-architecture-design.zh-CN.md`

**Product prototype:** `docs/prototypes/agora-real-team-workflow-prototype.html`

## Durable Rules

### Execution log

Every implementation batch must append an entry under `Execution Log` before the final response. Record date, scope, files changed, commit SHA, automated verification, black-box path and user result when available. Existing historical entries are never rewritten merely to match a newer roadmap.

### Real black-box acceptance

Product acceptance uses a real AI tool, a real local software project and running Agora services. Fake models, fake indexes, synthetic Harness objects and fixtures remain valid test doubles for automated tests, but do not count as product acceptance.

Black-box checks must exercise user-level behavior through an AI tool and Web UI. The user is not asked to call raw APIs.

### Customer-local source

Customer source code and uncommitted changes remain in the developer workspace or CI runner by default. Agora server-side repository initialization is an explicitly authorized import/testing capability, not the customer primary path.

### Harness and context

- AI tools call high-level Harness capabilities.
- Harness returns task-aware ContextBundles under a token budget.
- The customer's AI tool reads local code and generates ContextProposals.
- Agora governs immutable ContextRevisions, versions, approvals and distribution.
- Web UI is for governance, approval, audit and status, not daily coding.

### Work and governance

- WorkItem represents the real project task.
- WorkSession represents one user and AI tool execution.
- Project managers view WorkItems and delivery state.
- Technical leads or Context Stewards govern technical context and Skills.
- Quality conclusions must link to QualityEvidence.

### Development batch size

Implement and self-test a meaningful end-to-end capability before asking the user for black-box verification. Prepare temporary repositories, data and running services without asking the user to do setup that Agora or the development agent can do.

---

## Current Implementation Snapshot

As of 2026-08-14, the codebase is an original local team-trial build being migrated toward the canonical product:

- FastAPI backend with SQLAlchemy repositories.
- SQLite file database by default at `.agora/agora.db`.
- In-memory fake keyword/vector indexes, rebuilt from persisted assets on API startup.
- Project creation, listing, initialization, initialization job tracking and archiving.
- A legacy server-side local repository analysis path with remote fallback.
- Asset normalization and generated project overview assets.
- Token-budgeted ContextPack planning with source references through test indexes.
- Harness work lifecycle: start work, plan context, record events, close work.
- Development update capture from agent summaries, tests, and optional git diffs.
- Writeback draft, accept/reject review, accepted writeback re-indexing.
- Stdio MCP adapter for agent calls.
- Minimal Next.js admin UI for projects, assets, skills, sessions, context testing, and writeback review.

Important migration gaps:

- No WorkItem model separate from TaskSession.
- No ContextStream, immutable ContextRevision or ContextProposal concurrency model.
- No structured multi-dimensional freshness or Git/CI RevisionSignal.
- No WorkflowVersion, WorkflowExecution, WorkArtifact or QualityEvidence model.
- No production auth, project membership, scoped AI credential or RBAC.
- No real Qdrant/OpenSearch/Neo4j adapters wired into runtime.
- No background job queue or real Temporal worker.
- No outbox-based reliable projection pipeline.
- MCP tools do not yet implement the canonical Local Connector/Harness protocol.
- External task systems, docs systems, PR metadata, and CI integrations are not implemented.

Last recorded full baseline verification:

```bash
.venv/bin/pytest -q
# 67 passed

cd apps/web && npm run build
# passed
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

## P2: Real AI Tool Harness Foundation

**Goal:** Replace the legacy server-scanning demo as the primary experience with a real AI-tool-to-Harness path against customer-local projects.

**Status:** Next.

Scope:

- Define protocol versioning, stable error codes and idempotency keys.
- Add a minimal authenticated principal, ProjectMembership and separate human/AI-tool credentials for local team use.
- Derive org/user/project access from the authenticated principal; do not trust tenant identity from request payloads.
- Refactor repository writes behind command-level Unit of Work boundaries so one Harness command owns commit/rollback.
- Upgrade the stdio MCP adapter into the first Local Connector path.
- Add normalized RepositoryIdentity and sanitized LocalWorkspaceObservation.
- Add WorkItem and migrate TaskSession semantics to WorkSession.
- Upgrade `agora_start_work` to resolve Project and WorkItem and create/resume WorkSession. Version references are nullable and capability-gated until their owning phases land.
- Add multi-dimensional freshness response.
- Upgrade `agora_plan_context` to canonical `agora_prepare_context` while preserving query, intent, token budget and source refs.
- Apply token budget to the complete serialized L0/L1 ContextBundle, with deterministic trimming and separate L2 expansion budgets.
- Ensure local absolute paths and credential-bearing remotes are not sent or stored.
- Add a minimal real AI-tool black-box path and prepare all required local test data automatically.

Out of scope:

- Context approval and branch head merging; delivered in P3.
- Full configurable workflow execution; delivered in P4.
- SSO, configurable approval policy, retention and enterprise identity hardening; delivered in P7.
- Accepted ContextRevision, WorkflowVersion and SkillVersion pinning; introduced in P3, P4 and P5.

Exit criteria:

- A real AI tool opens a real local repository and calls Agora without manual project selection when identity is unambiguous.
- Harness returns Project, WorkItem, WorkSession, nullable version capabilities, structured context state and next actions.
- Existing P1 context can be returned only as explicitly provisional ContextBundle material; canonical accepted ContextRevision begins in P3.
- A missing/stale result asks the AI tool to generate locally; Agora does not read the local path.
- Retries do not duplicate WorkItem or WorkSession.
- Unit of Work tests prove failed Harness commands do not leave partial domain state.
- Full serialized L0/L1 responses remain within budget; each L2 fetch uses a separate limit.
- Full Python tests, Web build and the grouped real AI-tool black-box pass.

---

## P3: Context Governance and Automatic Freshness

**Goal:** Establish trusted, versioned team context that remains correct under multiple developers, branches and concurrent updates.

Scope:

- Add ContextStream per project/repository/branch.
- Add immutable ContextRevision with schema version, provenance and structured SourceAnchor.
- Add ContextProposal types: initial, refresh, task_update and correction.
- Add Proposal review states including request_changes and needs_rebase.
- Accept Proposal using expected head, target-stream branch validation, commit reachability evidence and optimistic concurrency.
- Keep feature-branch knowledge in a feature ContextStream or session-local context; update the default stream only after merge through a refresh Proposal.
- Add revision diff and lineage views in Web.
- Add Local Connector RevisionObservation processing and the normalized RevisionSignal contract.
- Leave real provider webhook/CI adapters and signed Push-path acceptance to P8.
- Add a local-AI-generated ContextProposal upload path.
- Add outbox events plus a minimal retrying, idempotent consumer for context head changes and rebuildable search projections.

Exit criteria:

- A real AI tool can generate an initial ContextProposal from a local repository and upload it.
- An authenticated human technical reviewer can approve it in Web and create the first accepted ContextRevision.
- A second AI tool reuses the accepted revision instead of repeating full analysis.
- A Local Connector observation updates freshness; the normalized RevisionSignal contract is integration-tested without claiming a real provider adapter.
- Two concurrent Proposals cannot silently overwrite each other.
- A feature-branch Proposal cannot update the default-branch ContextStream before merge reachability is proven.
- Revision content, provenance, approval and source anchors are auditable.
- An outbox consumer failure is retryable without duplicating projections or losing the committed context head.

---

## P4: Workflow Harness and Work Audit

**Goal:** Make project processes executable through AI tools while retaining human control and complete WorkItem-level audit.

Scope:

- Add WorkflowDefinition and immutable WorkflowVersion.
- Add WorkflowExecution and WorkflowStepRun state machines.
- Make one WorkItem-level WorkflowExecution authoritative for stage and status; WorkSessions contribute step attempts, artifacts and evidence but cannot overwrite WorkItem stage independently.
- Support lightweight, standard and high-risk project workflows.
- Add WorkArtifact, HumanConfirmation and artifact upload policies.
- Pin WorkflowVersion and ContextRevision when a WorkSession starts.
- Add `agora_complete_workflow_step` with prerequisite and role checks.
- Add close-work validation, local pending sync and idempotent resume.
- Build Web WorkItem detail with WorkSessions, steps, artifacts and confirmations.
- Migrate useful SessionEvent and development writeback data without losing history.

Exit criteria:

- A real AI tool executes analysis, design, review, implementation, self-test and delivery for a realistic WorkItem.
- Required artifacts are saved locally and synchronized to Agora according to policy.
- Human gates cannot be bypassed by a normal agent credential.
- The same WorkItem can contain multiple users and WorkSessions.
- Concurrent WorkSessions cannot independently advance the WorkItem beyond unmet WorkflowExecution prerequisites.
- A project manager can understand task progress without interpreting raw Session events.

---

## P5: Skill and Team Memory Governance

**Goal:** Turn approved team methods and repeated experience into versioned, reusable AI work capabilities.

Scope:

- Separate logical Skill from immutable SkillVersion.
- Migrate current candidate/draft/approved/deprecated behavior.
- Add SkillCandidate provenance from WorkItem, ContextProposal and artifacts.
- Add versioned trigger, input/output schema, instructions and risk constraints.
- Pin used SkillVersions to WorkSession and record SkillRun evidence.
- Add duplicate detection and repeated-experience suggestions.
- Add Web review, diff, publish, deprecate and usage history.
- Make ContextPlanner select only approved, applicable SkillVersions.

Exit criteria:

- A developer can submit a SkillCandidate during a real task.
- A reviewer can edit and approve it into a new SkillVersion.
- A later AI-tool task automatically receives and uses the approved version.
- Historical WorkSessions remain linked to the exact SkillVersion used.

---

## P6: Quality and Project Management

**Goal:** Give quality personnel and project managers trustworthy project status through AI tools and Web UI.

Scope:

- Add structured QualityEvidence for local tests, CI, review and risk findings.
- Distinguish evidence, AI inference and unverified claims.
- Aggregate project and WorkItem quality state.
- Add WorkItem dashboard, ownership, blockers, stage and pending approvals.
- Add `agora_get_project_status` and `agora_get_quality_status` Harness queries.
- Add quality gaps, missing evidence and regression risk views.
- Link ContextProposal, SkillCandidate, Workflow and QualityEvidence to WorkItem.

Exit criteria:

- A project manager can ask an AI tool for current WorkItems, stages, blockers and approvals.
- A quality user can ask for task/project quality and trace every result to evidence.
- Web and AI-tool views agree because both use the same WorkItem and evidence model.
- An AI summary cannot turn a failed or absent test into a passed state.

---

## P7: Team Governance and Security

**Goal:** Harden the minimal identity boundary from P2 into enterprise-grade tenant, project, approval and audit governance.

Scope:

- Add SSO and enterprise identity lifecycle on top of the existing User, Membership and ProjectMembership boundary.
- Harden Web authentication, token rotation, revocation and session management.
- Add production-scoped AI-tool tokens and CI service accounts.
- Add tenant administration, lifecycle and audit controls around the principal-derived boundary established in P2.
- Expand project roles and configurable ApprovalPolicy beyond the minimal human/agent separation.
- Restrict Context, Skill, Workflow and high-risk actions by role.
- Add secret-safe logging, audit metadata, retention and export controls.
- Add webhook signature validation and replay protection.
- Add optional tamper-evident audit export for enterprise deployment.

Exit criteria:

- Cross-organization and unauthorized project access are rejected and tested.
- AI credentials cannot approve team knowledge.
- Technical and process approvals follow project policy.
- Sensitive actions include actor, tool, request, target and decision audit data.

---

## P8: Integrations and Quiet Automation

**Goal:** Connect Agora to repository, CI, task and PR signals so context and project status stay current with minimal user interruption.

Scope:

- GitHub/GitLab/Gitee/self-hosted Git push and PR/MR signals.
- CI QualitySignal and signed test result import.
- Task-system WorkItem mapping, beginning with one real adapter.
- Resolve Project/WorkItem from task URL, PR, branch and repository identity.
- Optional docs/OpenAPI source anchors without making Agora a general document crawler.
- Background stale detection, approval routing and actionable notifications.
- Local Connector offline queue and sync diagnostics.
- Policy-controlled CI Agent generation of refresh Proposals.

Exit criteria:

- A merge changes ContextStream freshness automatically.
- The freshness change is driven by a real signed provider webhook or authenticated CI signal, not a synthetic contract call.
- An AI tool starting from a task or PR resolves the correct Project and WorkItem.
- CI evidence appears on the correct WorkItem without manual upload.
- Normal developer work remains silent unless a decision or conflict is required.

---

## P9: Production and Operations Readiness

**Goal:** Make Agora reliable to deploy, operate, upgrade and recover for a real software team.

Scope:

- Postgres and S3-compatible production configuration.
- Scale and operate the existing transactional outbox with worker concurrency, dead-letter diagnostics and rebuild tools.
- Containerized API, Web, worker and Local Connector distribution.
- Health, readiness, structured logs, request/trace IDs and metrics.
- Backup/restore, migration, rollback, data export and disaster recovery docs.
- Object retention, cleanup and audit archival.
- Performance and concurrency tests for Context head and Workflow commands.
- Evaluate Postgres FTS/pgvector with real retrieval data; add OpenSearch/Qdrant only if metrics require them.
- Upgrade and compatibility policy for Local Connector and MCP protocol.
- Deployed-environment smoke and full role-based black-box suite.

Exit criteria:

- A small team can deploy, onboard, work, review, upgrade, back up and recover Agora.
- Context and workflow concurrency invariants hold under load.
- Search projections can be rebuilt without loss of governance state.
- A production-like environment passes the complete Developer, Reviewer, Project Manager and Quality black-box journey.

---

## Historical Plan Files

The dated P0-P6 implementation plans describe work completed before the 2026-08-14 product realignment. They remain as implementation and test evidence, but they do not define the meaning of the realigned P2-P9 phases.

When a historical title conflicts with this Roadmap, this Roadmap and the canonical product/architecture documents take precedence.

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

### 2026-08-13: P5 Structured Development Closeout Audit

Scope:

- `close-work` now returns a structured `development_update` alongside the existing Markdown writeback.
- Structured closeout data includes summary, changed files, tests, risks, and follow-ups.
- `development_update_captured` session events now persist the structured closeout payload.
- Session audit API responses now include `development_updates` and a `development_updates` audit counter.
- The session audit detail page now has a first-class Development updates section before lower-level context, skill run, writeback, and timeline details.
- Black-box fixtures for this and future P5 work use China-oriented software R&D team scenarios, not manufacturing data.

Files changed:

- Modified: `packages/harness/development_capture.py`
- Modified: `packages/harness/service.py`
- Modified: `apps/api/routers/sessions.py`
- Modified: `apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx`
- Modified: `apps/web/app/styles.css`
- Modified: `tests/integration/api/test_harness_api.py`
- Modified: `tests/integration/api/test_sessions_api.py`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p5-session-audit.md`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_close_work_endpoint_can_prepare_development_update_from_repo_diff -v
# 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_sessions_api.py -v
# 6 passed

cd apps/web && npm run build
# passed
```

Black-box validation path:

- Open a closed work session generated from a software R&D fixture.
- Expected: the Session audit page shows Development updates with summary, changed files, tests, risks, follow-ups, writeback state, and the linked writeback ID.
- Expected: lower sections still show context packs, skill runs, writebacks, and timeline events.

Commit:

- `feat: structure development closeout audit`

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

### 2026-08-13: P6 Migration and Local Admin Baseline

Scope:

- Started P6 Production Persistence Baseline.
- Added Alembic configuration and an initial migration matching the current SQLAlchemy model schema.
- Added a guarded local admin CLI for rebuilding persisted asset indexes and resetting file-backed SQLite databases.
- Aligned local environment documentation with the runtime `AGORA_DATABASE_URL` variable.
- Added a P6 implementation plan file for remaining production persistence chunks.

Files changed:

- Created: `alembic.ini`
- Created: `alembic/env.py`
- Created: `alembic/script.py.mako`
- Created: `alembic/versions/20260813_0001_initial_schema.py`
- Created: `scripts/agora_admin.py`
- Created: `tests/integration/test_migrations.py`
- Created: `tests/integration/test_admin_cli.py`
- Created: `docs/superpowers/plans/2026-08-13-agora-p6-production-persistence.md`
- Modified: `.env.example`
- Modified: `README.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py tests/integration/test_admin_cli.py -v
# 4 passed

.venv/bin/pytest -q
# 66 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# passed
```

Black-box validation path:

- No immediate user validation required on 2026-08-13 because the user deferred black-box testing until tomorrow.
- Tomorrow, verify from the browser that the app still creates a software R&D project, initializes a repository, lists assets, and runs a context query after the P6 persistence baseline changes.

Commit:

- `feat: add persistence migration baseline`

### 2026-08-14: Web Dev Style Regression Fix

Scope:

- Fixed the Projects page appearing with browser-default styling during black-box validation.
- Root cause: `next build` was run while `next dev` was serving the same `.next` directory, leaving the dev page pointing at a CSS URL that returned 404.
- Added `apps/web/next.config.mjs` so development uses `.next-dev` and production build keeps using `.next`.
- Added `.next-dev/` to `.gitignore`.
- Updated Web TypeScript config to include `.next-dev/types/**/*.ts`.
- Added a regression test requiring separate dev/build dist directories.

Files changed:

- Created: `apps/web/next.config.mjs`
- Created: `tests/integration/test_web_config.py`
- Modified: `.gitignore`
- Modified: `apps/web/tsconfig.json`

Verification:

```bash
.venv/bin/pytest tests/integration/test_web_config.py -v
# 1 passed

.venv/bin/pytest -q
# 67 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# passed

curl http://127.0.0.1:3000/_next/static/css/app/layout.css?... 
# 200 text/css
```

Black-box validation path:

- Refresh `http://127.0.0.1:3000/projects`.
- Expected: the top nav, centered page container, project cards, buttons, muted text, and status badges render with Agora styling instead of browser-default link/input/button styles.

Commit:

- `4e316dd fix: isolate web dev build output`

### 2026-08-14: Product, Architecture and Roadmap Realignment

Scope:

- Re-reviewed Agora against the confirmed target: an agent-first team AI Project Harness with Web governance, approval, audit and visibility.
- Rewrote the canonical product design and technical architecture around the Local Connector, Harness Coordinator, WorkItem/WorkSession, versioned workflow, governed context and skill lifecycle.
- Realigned P2-P9 so each phase delivers a coherent, real AI-tool and Web black-box capability instead of test-only shortcuts.
- Updated the HTML prototype to reflect project management, context governance, workflow, skill approval, quality and AI-tool access.
- Consolidated durable content and deleted four superseded specification documents; retained historical phase plans with explicit historical labels.

Architecture review decisions:

- Customer code and documents remain local or in customer-controlled CI; the customer's real AI tool analyzes them.
- Agora stores and governs immutable ContextRevision, WorkflowVersion and SkillVersion records instead of pretending to analyze source code itself.
- One WorkItem-level WorkflowExecution is authoritative for task stage; WorkSessions contribute attempts, artifacts and evidence.
- Feature-branch context cannot update the default ContextStream until target-branch commit reachability is proven.
- P2 establishes the minimum authenticated human/AI-tool boundary and Unit of Work; later phases add version capabilities in their owning phase.
- The complete serialized L0/L1 ContextBundle is token-budgeted; L2 source expansion has a separate limit.
- Postgres is the source of truth, with transactional outbox-backed rebuildable projections.

Files changed:

- Canonical product design: `docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`
- Canonical technical design: `docs/superpowers/specs/2026-08-14-agora-technical-architecture-design.zh-CN.md`
- Canonical roadmap and execution log: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Product prototype: `docs/prototypes/agora-real-team-workflow-prototype.html`
- Historical guides and phase plans: marked as historical where they no longer define the target architecture.
- Deleted four duplicate or superseded specification files; Git history preserves their contents.

Verification:

```text
Independent specification review, round 1
# 7 blocking inconsistencies found and corrected

Independent specification review, round 2
# APPROVED; no remaining high- or medium-risk product/architecture/roadmap conflicts

Documentation consistency checks
# canonical_specs=2 roadmap_phases=9 prototype_screens=6 changed_markdown=11
# all changed Markdown local links resolve
# no references remain to the four deleted specifications

git diff --check
# passed

In-app browser prototype checks
# desktop 1280x720: six screens, branch guard present, no horizontal overflow
# mobile 390x844: six screens, responsive navigation, no horizontal overflow
```

Black-box validation:

- This change is design-only and does not claim an application capability as implemented.
- The prototype received a visual and responsive browser check; no fake AI service or test-only product path was added.
- Real application black-box validation resumes after the next full roadmap phase is implemented, using a real AI tool plus the running Agora Web UI.

Commit:

- `8d10ff9 docs: realign product architecture and roadmap`

### 2026-08-20: Realigned P2 Task 1 Data-Safe Schema Migration

Scope:

- Started the realigned P2 implementation from `docs/superpowers/plans/2026-08-14-agora-p2-real-ai-tool-harness-foundation.md`.
- Added schema ownership around existing P1 databases, including known unversioned P1 detection, backup-before-upgrade, schema fingerprint checks and refusal for unknown partial schemas.
- Added P2-compatible identity and work tables while preserving existing Projects, Assets, ContextPacks, Skills, SkillRuns, Writebacks, SessionEvents and legacy TaskSessions.
- Copied legacy TaskSession rows into WorkSession rows without changing historical session IDs.
- Verified the real local `.agora/agora.db` was inspected but not mutated during Task 1.

Files changed:

- Created: `alembic/versions/20260814_0002_p2_harness_foundation.py`
- Created: `packages/core/schema_manager.py`
- Modified: `packages/core/models.py`
- Modified: `packages/domain/enums.py`
- Modified: `apps/api/dependencies.py`
- Modified: `scripts/agora_admin.py`
- Added integration migration coverage in `tests/integration/test_p2_migration.py` and `tests/integration/test_migrations.py`.

Verification:

```text
.venv/bin/pytest tests/integration/test_p2_migration.py tests/integration/test_migrations.py -v
# passed after fixes

.venv/bin/pytest
# 88 passed at Task 1 completion

Independent specification review
# APPROVED after migration compatibility fixes

Independent code quality review
# APPROVED after hardening direct P2 migration guards
```

Commits:

- `19cebb4 feat: add p2 compatible work and identity schema`
- `f090e55 fix: migrate in-memory database on app engine`
- `9f72897 fix: harden p2 schema migration validation`
- `5c87a55 fix: guard direct p2 migration from corrupt legacy data`

### 2026-08-20: Realigned P2 Task 2 Unit of Work Boundary

Scope:

- Moved write ownership from repositories and domain services to explicit command-level `SqlAlchemyUnitOfWork` boundaries.
- Added rollback-on-exception, clean-exit rollback, explicit commit and nested-command protection.
- Hardened UoW so it rejects any pre-existing SQLAlchemy transaction, including outer `session.begin()` and SQLAlchemy autobegin from earlier reads.
- Updated HTTP mutation routes, worker/admin mutation paths and writeback/index flows to use explicit UoW ownership.
- Deferred post-commit search-index refresh from the database transaction, and made post-commit index failure return a committed response with `index_status: pending_rebuild` warnings instead of a false command failure.
- Made writeback acceptance retry idempotent when the writeback was already accepted, preserving the existing `accepted_asset_id` and avoiding duplicate Assets.
- Isolated failed SkillRun audit persistence so audit write failure does not mask the original business error.
- Added startup bootstrap seeding for built-in Skills on existing projects through an explicit UoW; `GET /skills` remains read-only.

Files changed:

- Created/modified: `packages/core/uow.py`
- Modified: `apps/api/main.py`
- Modified: `apps/api/routers/projects.py`
- Modified: `apps/api/routers/skills.py`
- Modified: `apps/api/routers/writebacks.py`
- Modified: `packages/core/services/skills.py`
- Modified: `packages/harness/memory_writeback.py`
- Added or extended tests in `tests/unit/core/test_uow.py`, `tests/unit/core/test_repositories.py`, `tests/integration/api/test_transaction_boundaries.py`, `tests/integration/api/test_initialization_jobs.py`, and `tests/integration/api/test_skills_api.py`.

Verification:

```text
.venv/bin/pytest tests/unit/core/test_uow.py tests/unit/core/test_repositories.py tests/integration/api/test_transaction_boundaries.py tests/integration/api/test_initialization_jobs.py tests/integration/api/test_skills_api.py -v
# 41 passed

.venv/bin/pytest
# 119 passed

git diff --check
# passed

Static commit guard
# no direct `.commit(` calls in repository/domain-service mutation modules

Independent code quality review
# APPROVED; no Critical or Important findings remain

Independent specification review
# APPROVED; targeted Task 2 checks passed with no compliance findings
```

Commits:

- `a36d10d refactor: own writes at unit of work boundaries`
- `18724e0 fix: isolate project initialization transactions`
- `ce06f3c fix: defer writeback indexing until commit`
- `39474ca test: guard draft writeback preparation`
- `0d5620c fix: isolate failed skill run audit`
- `1aaae0a fix: harden unit of work boundaries`

Current P2 status:

- Task 1 is complete.
- Task 2 is complete.
- Task 3 is complete.
- Task 4 is complete.
- Task 5 is complete.
- Task 6 is complete.
- Task 7 is complete.
- Next implementation target: Task 8, adding Web visibility for canonical P2 state.

### 2026-08-21: Realigned P2 Task 3 Local Team Principal Boundary

Scope:

- Added the minimum authenticated human and AI-tool boundary for the real AI-tool Harness path.
- Added bootstrap identity creation from `AGORA_BOOTSTRAP_HUMAN_TOKEN`, `AGORA_BOOTSTRAP_AGENT_TOKEN` and `AGORA_BOOTSTRAP_ORG_ID`.
- Persisted human and agent credentials as separate credential kinds for the same local bootstrap user.
- Stored credential secrets only as SHA-256 hashes and changed the diagnostic token prefix to a hash-derived non-secret value.
- Granted the bootstrap user membership to existing projects in the selected organization during startup.
- Enforced project membership on project, asset, session, skill, writeback and Harness routes.
- Made human-only actions require a human credential; agent credentials can use Harness paths but cannot create/archive projects or approve/govern Web assets.
- Made payload `org_id` subordinate to the authenticated principal organization for project creation.
- Wired Web server fetches to attach `AGORA_WEB_HUMAN_TOKEN` and MCP HTTP calls to attach `AGORA_AGENT_TOKEN` without serializing those tokens to the browser.
- Added explicit test bypass only for legacy test compatibility through `AGORA_TEST_AUTH_BYPASS=1`; production-like paths reject missing tokens.
- Fixed review findings so auth resolution no longer commits outside explicit UoW and diagnostic prefixes no longer contain bearer-token material.

Files changed:

- Created: `packages/core/auth.py`
- Created: `packages/core/repositories/identities.py`
- Created: `apps/api/auth.py`
- Modified: `apps/api/main.py`
- Modified: `apps/api/dependencies.py`
- Modified: `apps/api/routers/harness.py`
- Modified: `apps/api/routers/projects.py`
- Modified: `apps/api/routers/assets.py`
- Modified: `apps/api/routers/sessions.py`
- Modified: `apps/api/routers/skills.py`
- Modified: `apps/api/routers/writebacks.py`
- Modified: `apps/web/lib/api.ts`
- Modified: `apps/mcp/server.py`
- Modified: `.env.example`
- Modified: `infra/env.example`
- Added auth package markers for pytest import stability under `tests/**/__init__.py`.
- Added auth tests in `tests/unit/core/test_auth.py` and `tests/integration/api/test_auth.py`.
- Extended `tests/integration/test_web_config.py` and `tests/integration/api/test_transaction_boundaries.py`.

Verification:

```text
.venv/bin/pytest tests/unit/core/test_auth.py tests/integration/api/test_auth.py tests/integration/test_web_config.py -v
# 10 passed

.venv/bin/pytest tests/unit/core/test_auth.py tests/integration/api/test_auth.py tests/integration/test_web_config.py tests/integration/api/test_transaction_boundaries.py -q
# 23 passed after review fixes

.venv/bin/pytest
# 129 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed

Independent specification review
# APPROVED after fixing hash-derived token diagnostics and auth raw commit

Independent code quality review
# APPROVED; no Critical or Important findings remain
```

Commits:

- `ea9e91a feat: add local team principal boundary`
- `d417e47 fix: remove auth token leakage and raw commit`

### 2026-08-21: Realigned P2 Task 4 Work Items and Idempotent Work Sessions

Scope:

- Replaced new Harness session creation with WorkItem and WorkSession records.
- Added `WorkRepository` and `WorkResolver` for task-key, branch-hint and Chinese software R&D title resolution.
- Added listable WorkItem API under project membership scope.
- Made `agora_start_work` resolve Project first, then WorkItem, then WorkSession.
- Bound WorkSession `user_id` and `credential_id` to authenticated Principal values only.
- Added `IdempotencyRecord` handling for start-work keyed by authenticated credential, operation and idempotency key.
- Covered replay, payload conflict, expired tombstone and concurrent same-key behavior.
- Kept legacy Session pages and APIs readable through compatibility serializers, now including WorkItem details.
- Stopped new product start-work paths from creating `TaskSession` rows while leaving migrated legacy rows readable.
- Fixed review findings: no Service-level default auth bypass, MCP `branch_name` forwarding, Web WorkItem rendering, legacy session dedupe, and membership checks before work-item clarification.

Files changed:

- Created: `packages/core/repositories/work.py`
- Created: `packages/harness/work_resolver.py`
- Created: `apps/api/routers/work_items.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/service.py`
- Modified: `packages/harness/session_recorder.py`
- Modified: `packages/harness/task_resolver.py`
- Modified: `apps/api/routers/harness.py`
- Modified: `apps/api/routers/sessions.py`
- Modified: `apps/api/main.py`
- Modified: `apps/mcp/server.py`
- Modified: `apps/mcp/tools.py`
- Modified: Web Session list/detail pages.
- Added/extended WorkItem, Session, MCP and Harness tests.

Verification:

```text
.venv/bin/pytest tests/unit/harness/test_work_resolver.py tests/unit/harness/test_harness_service.py tests/integration/api/test_work_items_api.py tests/integration/api/test_sessions_api.py -v
# passed

.venv/bin/pytest tests/unit/harness/test_work_resolver.py tests/unit/harness/test_harness_service.py tests/integration/api/test_work_items_api.py tests/integration/api/test_sessions_api.py tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py tests/integration/api/test_auth.py tests/integration/test_web_config.py -q
# 34 passed after review fixes

.venv/bin/pytest
# 147 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed

Independent specification review
# APPROVED after review fixes

Independent code quality review
# APPROVED; no Critical or Important findings remain
```

Commits:

- `f58991e feat: add work items and idempotent work sessions`
- `40cef77 fix: close work session review gaps`

### 2026-08-24: P2 Task 5 MCP Local Repository Observer

Scope:

- Added a Local Connector domain model for sanitized local workspace observations.
- Added Git repository observation in the MCP stdio process using `AGORA_WORKSPACE_ROOT` or the current working directory.
- Normalized repository identity to host/path metadata and stripped Git username, password/token, URL scheme and `.git` suffix.
- Captured branch, head commit, dirty state and changed/untracked counts without sending absolute local paths, file names or source contents.
- Made `agora_start_work` attach local observation metadata automatically when the AI tool does not provide one.
- Let Harness resolve projects from sanitized local observation identity as well as legacy `repo_remote`.
- Rejected path-like `repo_remote` values at the API boundary.
- Added canonical start-work response envelope fields: `protocol_version`, `request_id`, `capabilities` and structured `next_actions`, while keeping legacy fields for P2 compatibility.
- Added canonical Harness error bodies for project resolution, WorkItem clarification and idempotency conflicts while retaining legacy `detail.code/message` fields.
- Proved the real stdio MCP process path with a local HTTP recorder and stderr log capture.

Verification:

```text
.venv/bin/pytest
# 157 passed

.venv/bin/pytest tests/unit/local_connector tests/unit/mcp tests/integration/mcp/test_local_connector_process.py -v
# 10 passed

git diff --check e0f78fa..HEAD
# passed
```

Commit:

- `5fa1b71 feat: observe local repositories through mcp connector`

### 2026-08-24: P2 Task 6 Budgeted Provisional ContextBundle

Scope:

- Added deterministic stable JSON token estimation and whole-payload trimming.
- Added `ContextBundle` construction that wraps legacy ContextPack material as `provisional=true`.
- Added canonical freshness dimensions for P2 without claiming accepted revisions, `fresh` coverage or exact repository relation.
- Added `recommended_action=use_provisional_context` when reusable legacy material exists and `analyze_local_project` when context is missing.
- Added `/harness/prepare-context` as the primary context preparation endpoint.
- Converted legacy `/harness/plan-context` into a compatibility adapter returning the canonical payload plus deprecation metadata, while preserving legacy fields such as `id`, `summary`, `level` and `source_refs`.
- Preserved legacy `context_planned` audit behavior for `/plan-context`; new `/prepare-context` records `context_prepared`.
- Added stable `TOKEN_BUDGET_TOO_SMALL` error handling with an `increase_token_budget` next action.

Verification:

```text
.venv/bin/pytest tests/unit/harness/test_token_budget.py tests/unit/harness/test_context_bundle.py tests/unit/harness/test_harness_service.py tests/integration/api/test_harness_api.py tests/unit/knowledge/test_context_engine.py -v
# 35 passed

.venv/bin/pytest
# 166 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```

Commit:

- `1bb3042 feat: prepare budgeted provisional context bundles`

### 2026-08-24: P2 Task 7 Canonical Harness API and MCP Tools

Scope:

- Added the P2 protocol-level E2E loop covering authenticated start-work, idempotency replay, prepare-context, fetch-context-ref, close-work and session audit events.
- Changed the advertised MCP tool list to the P2 canonical subset: `agora_start_work`, `agora_prepare_context`, `agora_fetch_context_ref`, `agora_close_work`.
- Added MCP `agora_prepare_context` dispatch to `/harness/prepare-context`.
- Kept legacy MCP dispatch for `agora_plan_context`, `agora_record_event`, `agora_prepare_writeback` and `agora_search_knowledge`, but made them non-advertised compatibility tools with deprecation metadata.
- Removed `not_implemented` fallback from the advertised fetch-context tool path.
- Added the P2 MCP compatibility table to the technical architecture document.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py tests/unit/mcp tests/e2e/test_p2_harness_loop.py -v
# 19 passed

.venv/bin/pytest
# 169 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```

Commit:

- `9f2512a feat: publish canonical p2 harness tools`
