# Agora P1-P9 Roadmap and Execution Log

> **Purpose:** This is Agora's durable implementation roadmap and recovery log. It must be sufficient to recover product direction, completed work and verification evidence after chat history is lost.

**Current branch:** `codex/agora-p0`

**Current baseline:** P0-P8 are implemented on the realigned Agent-first, Harness-first architecture. P9 operations readiness foundation is in progress.

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

**Status:** Implemented; pending user black-box validation.

Current plan:

- `docs/superpowers/plans/2026-08-26-agora-p5-skill-governance.md`

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

**Status:** Implemented enough for black-box validation; QualityEvidence, AI-tool status queries, MCP registration and Web project status are available.

Current plan:

- `docs/superpowers/plans/2026-08-26-agora-p6-quality-project-status.md`

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

Current implementation:

- `QualityEvidence` persists local tests, CI, review and risk findings with project, WorkItem, WorkSession and user provenance.
- AI tools can call `agora_record_evidence`, `agora_get_quality_status` and `agora_get_project_status`.
- Web users can open the project status page from project detail and see WorkItem counts, quality states and pending approvals.
- Project status now includes delivery readiness, blockers, quality dimensions and latest per-WorkItem evidence rows.
- Missing evidence is reported as `unverified`; failed evidence is reported as `failing`.
- Black-box guide: `docs/development/p6-quality-project-status-blackbox.zh-CN.md`

---

## P7: Team Governance and Security

**Goal:** Harden the minimal identity boundary from P2 into enterprise-grade tenant, project, approval and audit governance.

**Status:** In progress; approval RBAC and security audit foundation implemented.

Current plan:

- `docs/superpowers/plans/2026-08-26-agora-p7-governance-security.md`

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

Current implementation:

- Project knowledge approvals require human credentials plus owner/admin/reviewer project role.
- Agent approval attempts return `HUMAN_CREDENTIAL_REQUIRED`.
- Human project members without approval role return `PROJECT_ROLE_REQUIRED`.
- ContextProposal and Skill approval allow/deny decisions create `security_audit_events`.
- Web users can inspect project `Security audit` from the project detail page.
- Black-box guide: `docs/development/p7-governance-security-blackbox.zh-CN.md`

---

## P8: Integrations and Quiet Automation

**Goal:** Connect Agora to repository, CI, task and PR signals so context and project status stay current with minimal user interruption.

**Status:** Implemented enough for black-box validation; CI QualitySignal, repository RevisionSignal, PR/MR signal ingestion and external task WorkItem mapping are available.

Current plan:

- `docs/superpowers/plans/2026-08-26-agora-p8-integrations-automation.md`

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

Current implementation:

- Optional `AGORA_BOOTSTRAP_CI_TOKEN` creates a CI service credential.
- `POST /integrations/ci/quality-signal` requires CI credentials.
- CI signals resolve or create WorkItems by `work_item_key`.
- CI signals write P6 `QualityEvidence` with source/evidence type `ci`.
- The response returns project status so CI evidence immediately affects delivery readiness, blockers and quality dimensions.
- `POST /integrations/repository/revision-signal` stores repository signals and creates a submitted refresh ContextProposal when accepted context is stale.
- `POST /integrations/repository/pull-request-signal` stores PR/MR signals, resolves Project from repository identity, resolves WorkItem from task URL/key/title/branch and creates a submitted refresh ContextProposal when a merge advances the target branch beyond accepted context.
- CI and repository signals accept `task_provider`, `task_key` and `task_url`, then upsert a stable external task link for the WorkItem.
- `agora_get_project_status` and Web `Project status` expose WorkItem `task_links` so PM/QA/developers can trace Jira/飞书项目/禅道/GitLab/GitHub task references without manually managing Agora IDs.
- Black-box guide: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`

---

## P9: Production and Operations Readiness

**Goal:** Make Agora reliable to deploy, operate, upgrade and recover for a real software team.

**Status:** In progress; readiness/metrics, production-like container runtime assets and black-box operations guide are implemented.

Current plan:

- `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`

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

Current implementation:

- `GET /health` returns process liveness.
- `GET /ready` verifies database connectivity, Alembic schema revision and required runtime configuration.
- `GET /metrics` exposes Prometheus-style ready/schema/project/pending-context counters.
- API responses include `X-Request-ID`, preserving caller-supplied values for CI, AI-tool and Web correlation.
- Docker runtime assets exist for API, Web and Local Connector/MCP.
- `infra/docker-compose.yml` runs API, Web, Local Connector and dependency services with API/Postgres health checks.
- `.env.example` includes production-like database/token defaults, including CI service token.
- `scripts.agora_admin backup-sqlite` and `restore-sqlite` support local/SQLite backup and recovery drills.
- `scripts.agora_admin export-project` writes project governance archives as JSONL plus a manifest for audit, migration dry-runs and offline review.
- `scripts.agora_admin project-summary`, `GET /projects/{project_id}/operations-summary` and Web `Operations summary` expose the same persisted governance summary.
- `scripts.agora_admin outbox-summary` and `/metrics` expose outbox backlog, retryable and dead-letter diagnostics.
- `scripts.agora_admin smoke` verifies deployed API readiness, metrics and optional Web reachability.
- Black-box guide: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`

---

## Historical Plan Files

The dated P0-P6 implementation plans describe work completed before the 2026-08-14 product realignment. They remain as implementation and test evidence, but they do not define the meaning of the realigned P2-P9 phases.

When a historical title conflicts with this Roadmap, this Roadmap and the canonical product/architecture documents take precedence.

---

## Execution Log

### 2026-08-26: P8 CI QualitySignal Ingestion

Scope:

- Added optional CI service credential bootstrap via `AGORA_BOOTSTRAP_CI_TOKEN`.
- Added `POST /integrations/ci/quality-signal`.
- Restricted CI quality-signal ingestion to CI credentials with stable error code `CI_CREDENTIAL_REQUIRED`.
- Resolved or created WorkItems by CI `work_item_key`.
- Stored CI results as P6 `QualityEvidence` and returned P6 project status.
- Fixed `get-project-status` transaction ordering so production-auth callers can query it repeatedly.
- Added P8 CI black-box validation guide.

Files changed:

- Created: `apps/api/routers/integrations.py`
- Created: `tests/integration/api/test_integrations_api.py`
- Created: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Created: `docs/superpowers/plans/2026-08-26-agora-p8-integrations-automation.md`
- Modified: `packages/core/auth.py`
- Modified: `apps/api/auth.py`
- Modified: `apps/api/main.py`
- Modified: `apps/api/routers/harness.py`
- Modified: `tests/integration/api/test_auth.py`
- Modified: `tests/integration/test_web_config.py`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_auth.py::test_ci_bootstrap_token_is_service_scoped_and_cannot_create_projects
# failed first, then 1 passed

.venv/bin/pytest tests/integration/api/test_integrations_api.py
# failed first, then 2 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`.

Commit:

- `e337cf4 feat: ingest ci quality signals`

### 2026-08-26: P8 Repository RevisionSignal Automation

Scope:

- Added `repository_revision_signals` persistence.
- Added `POST /integrations/repository/revision-signal` for authenticated CI/repository automation.
- Compared observed repository branch heads against accepted ContextRevision commit SHA.
- Created submitted refresh ContextProposals when accepted project context is stale.
- Updated P8 black-box guide to cover CI evidence and repository freshness automation.

Files changed:

- Created: `alembic/versions/20260826_0010_p8_repository_revision_signals.py`
- Created: `packages/core/repositories/integrations.py`
- Modified: `packages/core/models.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `apps/api/routers/integrations.py`
- Modified: `tests/integration/test_migrations.py`
- Modified: `tests/integration/api/test_integrations_api.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p8-integrations-automation.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_repository_revision_signal_schema_links_project_and_work_item tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first, then 3 passed

.venv/bin/pytest tests/integration/api/test_integrations_api.py::test_repository_revision_signal_marks_context_stale_and_creates_refresh_proposal
# failed first, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`.

Commit:

- `397f224 feat: ingest repository revision signals`

### 2026-08-26: P8 External Task WorkItem Mapping

Scope:

- Added `work_item_links` persistence for external task-system identities.
- Enforced stable project + provider + external key identity for WorkItem mapping.
- Extended CI QualitySignal and repository RevisionSignal with `task_provider`, `task_key` and `task_url`.
- Returned `task_link` from both integration endpoints and reused the same link across signals.
- Added `task_links` to `agora_get_project_status` WorkItems.
- Rendered external task links in Web `Project status`.
- Updated the P8 black-box guide to validate AI/CI-driven WorkItem mapping without manual HTTP calls.

Files changed:

- Created: `alembic/versions/20260826_0011_p8_work_item_links.py`
- Modified: `packages/core/models.py`
- Modified: `packages/core/repositories/work.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/service.py`
- Modified: `apps/api/routers/integrations.py`
- Modified: `apps/web/app/projects/[projectId]/status/page.tsx`
- Modified: `tests/integration/test_migrations.py`
- Modified: `tests/integration/api/test_integrations_api.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p8-integrations-automation.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_work_item_links_schema_enforces_project_provider_key_identity tests/integration/api/test_integrations_api.py::test_ci_quality_signal_records_evidence_and_updates_project_status tests/integration/api/test_integrations_api.py::test_repository_revision_signal_reuses_existing_task_link_work_item tests/integration/test_web_config.py::test_project_status_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first, then 5 passed
```

Black-box validation path:

- Use `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`.

Commit:

- `49f3491 feat: map external task links`

### 2026-08-26: P8 PR/MR Signal Automation

Scope:

- Added `pull_request_signals` persistence.
- Added `POST /integrations/repository/pull-request-signal`.
- Resolved Project from `repository_identity` when Agora project id is not supplied.
- Resolved WorkItem from explicit task key, task URL, PR/MR title or source branch.
- Reused external task WorkItem mapping for PR/MR signals.
- Created submitted refresh ContextProposals when merged PR/MR signals advance the target branch beyond accepted context.
- Updated the P8 black-box guide with a PR/MR merge path.

Files changed:

- Created: `alembic/versions/20260826_0012_p8_pull_request_signals.py`
- Modified: `packages/core/models.py`
- Modified: `packages/core/repositories/integrations.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `apps/api/routers/integrations.py`
- Modified: `tests/integration/test_migrations.py`
- Modified: `tests/integration/api/test_integrations_api.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p8-integrations-automation.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_pull_request_signals_schema_links_project_work_item_and_actor tests/integration/api/test_integrations_api.py::test_pull_request_signal_resolves_project_from_repository_and_creates_refresh_proposal tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first, then 3 passed
```

Black-box validation path:

- Use `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`.

Commit:

- `bf502d3 feat: ingest pull request signals`

### 2026-08-26: P9 Operations Readiness Foundation

Scope:

- Added `/ready` readiness checks for database, schema revision and runtime configuration.
- Added `/metrics` Prometheus-style operational counters.
- Added API, Web and Local Connector Dockerfiles.
- Expanded Docker Compose from dependency-only services to a production-like API/Web/connector stack.
- Added API and Postgres health checks.
- Updated `.env.example` for production-like runtime and CI service token.
- Added P9 operations black-box guide covering health/readiness/metrics, PostgreSQL, backup/restore and Developer/Reviewer/Project Manager/Quality smoke paths.

Files changed:

- Created: `infra/Dockerfile.api`
- Created: `infra/Dockerfile.web`
- Created: `infra/Dockerfile.local-connector`
- Created: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Created: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `.env.example`
- Modified: `infra/docker-compose.yml`
- Modified: `apps/api/routers/health.py`
- Modified: `tests/unit/test_health.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/unit/test_health.py::test_readiness_endpoint_reports_database_schema_and_configuration tests/unit/test_health.py::test_metrics_endpoint_exposes_prometheus_style_operational_counters tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first, then 3 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p9_container_runtime_assets_exist
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`.

Commit:

- `5efcda9 feat: add p9 operations readiness foundation`

### 2026-08-26: P9 SQLite Backup and Recovery CLI

Scope:

- Added `backup-sqlite` admin CLI command using SQLite online backup API.
- Added `restore-sqlite` admin CLI command with explicit `--yes` replacement confirmation.
- Verified restored databases keep persisted project data and remain schema-managed.
- Updated the P9 black-box guide with separate SQLite and PostgreSQL recovery paths.

Files changed:

- Modified: `scripts/agora_admin.py`
- Modified: `tests/integration/test_admin_cli.py`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_backup_and_restore_sqlite_database
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`.

Commit:

- `df1c20c feat: add sqlite backup recovery commands`

### 2026-08-26: P9 Project Governance Export Archive

Scope:

- Added `export-project` admin CLI command.
- Exported project-scoped governance tables as JSONL files.
- Wrote `manifest.json` with schema revision, project identity, file counts and relationship ids.
- Updated the P9 black-box guide with project archive validation.

Files changed:

- Modified: `scripts/agora_admin.py`
- Modified: `tests/integration/test_admin_cli.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_export_project_archive_writes_manifest_and_jsonl_assets
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`.

Commit:

- `889e952 feat: export project governance archive`

### 2026-08-26: P9 Deployment Smoke Command

Scope:

- Added `smoke` admin CLI command for deployment validation.
- Checked running API `/ready` and required `status = ready`.
- Checked running API `/metrics` and required `agora_ready 1`.
- Checked optional Web base URL.
- Updated P9 black-box guide with deployment smoke command usage.

Files changed:

- Modified: `scripts/agora_admin.py`
- Modified: `tests/integration/test_admin_cli.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_smoke_checks_api_readiness_metrics_and_web
# failed first, then 1 passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`.

Commit:

- `c6124e1 feat: add deployment smoke command`

### 2026-08-27: P9 Request Tracing Headers

Scope:

- Added API request id middleware.
- Generated `X-Request-ID` for requests that do not provide one.
- Preserved incoming `X-Request-ID` values for caller correlation.
- Attached request id headers to normal and error responses.
- Updated the P9 black-box guide with request-id validation.

Files changed:

- Created: `apps/api/middleware.py`
- Modified: `apps/api/main.py`
- Modified: `tests/unit/test_health.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/unit/test_health.py::test_api_generates_request_id_for_every_response tests/unit/test_health.py::test_api_preserves_incoming_request_id tests/unit/test_health.py::test_api_adds_request_id_to_error_responses tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first, then 4 passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`.

Commit:

- `06a8962 feat: add request tracing headers`

### 2026-08-27: P9 Project Operations Summary

Scope:

- Added shared project operations summary service over persisted governance tables.
- Added `project-summary` admin CLI command.
- Added `GET /projects/{project_id}/operations-summary`.
- Added Web `Operations summary` page and project-home entry.
- Included assets, work items, context governance, quality evidence, skills, approvals, security audit, repository signals and PR/MR signals.
- Updated P9 black-box guide with Web and CLI validation.

Files changed:

- Created: `packages/core/services/project_summary.py`
- Modified: `scripts/agora_admin.py`
- Modified: `apps/api/routers/projects.py`
- Created: `apps/web/app/projects/[projectId]/operations/page.tsx`
- Modified: `apps/web/app/projects/[projectId]/page.tsx`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Modified: `tests/integration/test_admin_cli.py`
- Modified: `tests/integration/api/test_projects_api.py`
- Modified: `tests/integration/test_web_config.py`

Verification:

```bash
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_project_summary_reports_governance_and_delivery_state tests/integration/api/test_projects_api.py::test_project_operations_summary_api_reports_project_governance_state tests/integration/test_web_config.py::test_p9_operations_summary_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first, then 4 passed
.venv/bin/pytest
# 247 passed, 2 skipped
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`, step 9.

Commit:

- `daf2c0e feat: add project operations summary`

### 2026-08-27: P9 Outbox Operations Diagnostics

Scope:

- Added reusable outbox diagnostics summary over persisted `outbox_events`.
- Added `outbox-summary` admin CLI command with optional JSON output.
- Reported total outbox events, by-status counts, by-type counts, retryable count and dead-letter samples.
- Added Prometheus metrics for `agora_outbox_events_total` and `agora_outbox_retryable_total`.
- Updated P9 black-box guide with outbox diagnostics validation.

Files changed:

- Created: `packages/core/services/outbox_diagnostics.py`
- Modified: `apps/api/routers/health.py`
- Modified: `scripts/agora_admin.py`
- Modified: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p9-operations-readiness.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Modified: `tests/unit/test_health.py`
- Modified: `tests/integration/test_admin_cli.py`
- Modified: `tests/integration/test_web_config.py`

Verification:

```bash
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_outbox_summary_reports_backlog_and_dead_events tests/unit/test_health.py::test_metrics_endpoint_exposes_outbox_backlog_counters tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first, then 3 passed
.venv/bin/pytest
# 249 passed, 2 skipped
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# passed
```

Black-box validation path:

- Use `docs/development/p9-operations-readiness-blackbox.zh-CN.md`, step 10.

Commit:

- `3158800 feat: add outbox operations diagnostics`

### 2026-08-26: P7 Approval RBAC and Security Audit

Scope:

- Added `security_audit_events` schema and runtime support.
- Added approval role helpers on ProjectMembership roles.
- Restricted ContextProposal and Skill approvals to human owner/admin/reviewer credentials.
- Recorded security audit events for approval allow and deny decisions.
- Added project-scoped security audit API and Web `Security audit` page.
- Added P7 black-box validation guide.

Files changed:

- Created: `alembic/versions/20260826_0009_p7_security_audit.py`
- Created: `packages/core/repositories/security.py`
- Created: `apps/web/app/projects/[projectId]/security/page.tsx`
- Created: `docs/development/p7-governance-security-blackbox.zh-CN.md`
- Modified: `packages/core/models.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/core/auth.py`
- Modified: `apps/api/auth.py`
- Modified: `apps/api/routers/context_governance.py`
- Modified: `apps/api/routers/skills.py`
- Modified: `apps/api/routers/projects.py`
- Modified: `apps/web/app/projects/[projectId]/page.tsx`
- Modified: P7 migration, API and Web configuration tests.

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py::test_p7_security_audit_schema_links_actor_and_project tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first, then 3 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py::test_context_approval_rejects_agent_and_non_reviewer_member_with_audit
# failed first, then 1 passed

.venv/bin/pytest tests/integration/api/test_skills_api.py::test_skill_approval_rejects_agent_and_non_reviewer_member_with_audit
# failed first, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p7_security_audit_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p7_governance_security_blackbox_guide_exists
# failed first, then 2 passed
```

Black-box validation path:

- Use `docs/development/p7-governance-security-blackbox.zh-CN.md`.

Commit:

- `14036a5 feat: add p7 approval governance audit`

### 2026-08-26: P6 Quality and Project Status Foundation

Scope:

- Added the P6 `QualityEvidence` persistence model and migration.
- Added Harness/API/MCP capabilities for recording quality evidence and retrieving WorkItem/project quality status.
- Added project-manager status aggregation across WorkItems, quality states and pending context/skill approvals.
- Added the Web project status page and project-detail navigation entry.
- Kept AI inference separate from evidence: missing quality evidence is `unverified`, and failed evidence remains `failing`.

Files changed:

- Created: `alembic/versions/20260826_0008_p6_quality_evidence.py`
- Created: `packages/core/repositories/quality.py`
- Created: `apps/web/app/projects/[projectId]/status/page.tsx`
- Modified: `packages/core/models.py`
- Modified: `packages/core/services/runtime.py`
- Modified: `packages/harness/service.py`
- Modified: `apps/api/routers/harness.py`
- Modified: `apps/mcp/tools.py`
- Modified: `apps/mcp/server.py`
- Modified: `apps/web/app/projects/[projectId]/page.tsx`
- Modified: P6 migration, Harness API, MCP and Web configuration tests.

Verification:

```bash
.venv/bin/pytest tests/integration/test_migrations.py tests/integration/api/test_harness_api.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/integration/test_web_config.py
# 60 passed
```

Black-box validation path:

- Pending. Prepare after the remaining P6 quality dashboard and project-management views are implemented into one larger validation batch.

Commit:

- `8e9f647 feat: add p6 quality project status foundation`

### 2026-08-26: P6 Delivery Readiness and Evidence Drill-down

Scope:

- Added `delivery_readiness` to project status so project managers can distinguish ready, at-risk, needs-evidence and blocked states.
- Added project blockers derived from blocked WorkItems and failed quality evidence.
- Added quality dimensions grouped by evidence type and status.
- Added latest per-WorkItem evidence rows to project status and rendered them in the Web project status page.

Files changed:

- Modified: `packages/harness/service.py`
- Modified: `apps/web/app/projects/[projectId]/status/page.tsx`
- Modified: `tests/integration/api/test_harness_api.py`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p6-quality-project-status.md`

Verification:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_project_status_aggregates_work_items_quality_and_pending_approvals
# failed first, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_project_status_page_is_available_and_linked_from_project_home
# failed first, then 1 passed
```

Black-box validation path:

- Pending. This should be grouped with the remaining P6 black-box guide.

Commit:

- `40ae08c feat: add p6 delivery readiness status`

### 2026-08-26: P6 Black-box Validation Guide

Scope:

- Added the P6 black-box guide for AI-tool and Web validation.
- Covered passed evidence, failed evidence, missing evidence, project status aggregation, delivery readiness, blockers and pending approvals.
- Repeated the acceptance boundary that users do not manually call raw HTTP APIs.

Files changed:

- Created: `docs/development/p6-quality-project-status-blackbox.zh-CN.md`
- Modified: `tests/integration/test_web_config.py`
- Modified: `docs/superpowers/plans/2026-08-26-agora-p6-quality-project-status.md`
- Modified: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

Verification:

```bash
.venv/bin/pytest tests/integration/test_web_config.py::test_p6_quality_project_status_blackbox_guide_exists
# 1 passed
```

Black-box validation path:

- Use `docs/development/p6-quality-project-status-blackbox.zh-CN.md`.

Commit:

- `728e2c2 docs: add p6 blackbox validation guide`

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

### 2026-08-24: P2 Task 8 Web Visibility for Work and Context State

Scope:

- Added safe WorkItem list/detail API projections for Web, including participants, latest context state, WorkSessions and nullable P2 capability pins.
- Added WorkItems list and WorkItem detail pages under each project.
- Linked Session list/detail pages back to their WorkItem.
- Changed the product Context page from an execution tester into a read-only context-state audit view.
- Removed Web-side agent simulation routes for context submit and development capture from the product route tree.
- Updated restrained operational styling for WorkItem tables, mobile layout and navigation.
- Preserved the product boundary: Web visualizes project state; AI tools use the canonical Harness to start work, prepare context, fetch context refs and close work.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_work_items_api.py tests/integration/test_web_config.py -q
# 10 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

.venv/bin/pytest
# 173 passed

Browser validation
# Production-style local API/Web services with human/agent bearer tokens, no AGORA_TEST_AUTH_BYPASS.
# Verified project home, WorkItems list, WorkItem detail and Context state at 1440x900 and 390x844.
# No hidden Context Tester text, no Web agent-simulation entry, no horizontal overflow, and styled shell loaded.
```

Commit:

- `5411a14 feat: expose p2 work state in web`

### 2026-08-24: P2 Task 9 Real AI Tool Black-box Preparation

Scope:

- Added `scripts/prepare_p2_blackbox.py` to idempotently prepare a realistic `Payments Core` local repository for issue `PAY-241`.
- The setup command uses production-style bearer tokens and public FastAPI project/initialization routes in-process.
- The setup command creates project assets only; it does not precompute AI context, create WorkSessions or fake AI tool results.
- Added Chinese black-box instructions for AI-tool operation and Web verification.
- Added Postgres semantic tests gated by `AGORA_TEST_POSTGRES_URL`.
- Ran a SQLite migration rehearsal against a copy of the current local `.agora/agora.db`; the live database was not mutated.

Verification:

```text
.venv/bin/pytest tests/integration/test_p2_blackbox_setup.py tests/integration/test_p2_postgres.py -q
# 1 passed, 2 skipped

.venv/bin/pytest
# 174 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

SQLite migration rehearsal
# action=stamp_0001_and_upgrade revision=20260814_0002
# projects/assets/task_sessions/writebacks/skills counts preserved; work_sessions backfilled from 0/missing to 43

Postgres runtime verification
# not executed locally because docker is unavailable; AGORA_TEST_POSTGRES_URL-gated tests are present.
```

Status:

- P2 remains active until Postgres runtime verification and the user-confirmed real AI-tool/Web black-box pass.

Commit:

- `85b54f0 docs: prepare p2 real ai tool acceptance`

### 2026-08-24: P3 Task 1 Context Governance Foundation

Scope:

- Added current P3 implementation plan for Context Governance.
- Added `context_streams`, `context_revisions`, `context_proposals`, `approval_decisions` and `outbox_events`.
- Added project context governance API under `/projects/{project_id}/context`.
- AI/agent credentials can submit ContextProposal as reviewable candidate state; this does not directly create accepted context.
- Human approval uses expected stream head and RevisionSignal evidence to create immutable ContextRevision, update stream head and emit `context_head_changed` outbox in one transaction.
- Stale proposal acceptance returns 409 and marks the proposal `needs_rebase`.
- `agora_prepare_context` now returns `fresh` coverage and pins `context_revision_id` when an accepted head revision exists; otherwise P2 provisional behavior remains.
- Web Context state page now shows ContextStreams and ContextProposals as read-only governance state.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/integration/test_p3_context_governance_migration.py -q
# 3 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/unit/harness/test_context_bundle.py tests/unit/harness/test_harness_service.py tests/integration/api/test_harness_api.py -q
# 28 passed

.venv/bin/pytest
# 178 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

Browser validation
# 1440x900 and 390x844 Context page checks passed; streams/proposals visible, no old tester entry, no horizontal overflow.
```

Next:

- Add canonical Harness/MCP proposal upload path so AI tools can submit ContextProposal without using project Web/API routes directly.

### 2026-08-24: P3 Task 2 Real AI-tool ContextProposal Upload Path

Scope:

- Added canonical `/harness/submit-context-proposal` for authenticated AI tools.
- Proposal submission now resolves project, stream and WorkItem from the active WorkSession, so AI tools do not need to call Web management routes or pass project internals.
- Submitting a proposal remains review-only: it creates `ContextProposal` with status `submitted`, but does not create accepted `ContextRevision`.
- The Harness response returns `protocol_version`, `operation=submit_context_proposal`, the proposal, stream state, current context revision pin and a `human_review_context_proposal` next action.
- Advertised `agora_submit_context_proposal` in the stdio MCP tool list and dispatches it to `/harness/submit-context-proposal`.
- Added in-process `AgoraMcpTools.agora_submit_context_proposal` delegation.
- Updated start-work capability advertisement to show `context_revisions=true` for the P3 upload path.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_context_governance_api.py::test_ai_tool_submits_context_proposal_through_harness_session tests/unit/mcp/test_stdio_server.py::test_stdio_mcp_server_lists_agora_tools tests/unit/mcp/test_stdio_server.py::test_stdio_submit_context_proposal_dispatches_to_harness tests/unit/mcp/test_tools.py::test_mcp_submit_context_proposal_delegates_to_harness
# 4 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py
# 13 passed

.venv/bin/pytest
# 181 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```

Next:

- Add Web proposal detail/review workflow so humans can inspect AI-generated proposals and approve them without calling APIs manually.

### 2026-08-24: P3 Task 3 Web ContextProposal Review Workflow

Scope:

- Added proposal detail links from the Context state page.
- Added a Web proposal detail page that shows proposal summary, status, expected/current stream head, target commit, accepted revision, content, source anchors and provenance.
- Added human review form with RevisionSignal fields: expected head, observed head SHA and target commit reachability.
- Added a Next approval route that submits to the existing FastAPI human approval API and revalidates Context pages.
- Approval errors redirect back to the detail page with a visible error message.
- Approved proposals hide the approval form and show accepted revision state.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_product_context_page_is_read_only_audit_view tests/integration/test_web_config.py::test_context_proposal_review_pages_are_available
# 2 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

Browser validation with temporary SQLite database, local API :18100 and Web :13100
# Context page showed AI-submitted PAY-318 proposal and View proposal link.
# Proposal detail showed Human review, Revision signal, source anchor and default target commit signal.
# Browser approval POST returned to detail page with approved status, accepted revision present and approval form hidden.
# 390x844 mobile viewport showed proposal detail without horizontal overflow.

.venv/bin/pytest
# 182 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```

Next:

- Add outbox consumer retry semantics and idempotent projection updates.

### 2026-08-25: P3 Task 4 Outbox Retry Consumer and Context-head Projection

Scope:

- Added `outbox_events.last_error` in migration `20260825_0004` for retry/dead-letter diagnostics.
- Added `OutboxProcessor` for stable batch processing of pending and retryable failed outbox events.
- Successful events are marked `completed` and skipped on later runs, preserving idempotent processing.
- Failed attempts increment `attempts`; retryable failures remain `failed`; events become `dead` at the configured retry limit.
- Added worker workflow handler for `context_head_changed` that validates stream head, accepted revision and proposal consistency before marking the event complete.
- Added runnable worker command: `python -m apps.workers.main outbox-once`.

Verification:

```text
.venv/bin/pytest tests/integration/workers/test_outbox_processor.py
# 5 passed

.venv/bin/pytest tests/integration/workers/test_outbox_processor.py tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine tests/integration/test_p3_context_governance_migration.py
# 8 passed

AGORA_DATABASE_URL=sqlite+pysqlite:////Users/daniel/Documents/Agora/.worktrees/agora-p0/.agora/outbox-cli-smoke.db .venv/bin/python -m apps.workers.main outbox-once --limit 5
# outbox processed=0 completed=0 failed=0 dead=0

.venv/bin/pytest
# 187 passed, 2 skipped

git diff --check
# passed
```

Next:

- Add branch-stream rules for feature branch proposals and merge reachability signals.

### 2026-08-25: P3 Task 5 Branch Stream Rules and Merge Reachability Signal

Scope:

- Feature branch proposals now update their own branch ContextStream and do not overwrite the default branch stream.
- RevisionSignal now includes `merge_target_branch` and `merged_to_target`.
- Default-branch approval is blocked when proposal provenance says the source context came from a feature branch and merge reachability is not proven.
- Accepted ContextRevision provenance records the normalized RevisionSignal used for approval.
- Web proposal review form now exposes merge target branch and merged-to-target fields.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_context_governance_api.py::test_feature_branch_context_proposal_updates_feature_stream_without_overwriting_main tests/integration/api/test_context_governance_api.py::test_feature_branch_context_cannot_update_default_stream_without_merge_signal
# 2 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/integration/test_web_config.py::test_context_proposal_review_pages_are_available
# 7 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

.venv/bin/pytest
# 189 passed, 2 skipped

git diff --check
# passed
```

Next:

- Prepare full P3 black-box validation steps.

### 2026-08-25: P3 Task 6 Black-box Validation Guide

Scope:

- Added `docs/development/p3-context-governance-blackbox.zh-CN.md`.
- The guide covers service startup, real AI-tool ContextProposal upload, Web human review, accepted ContextRevision reuse, feature branch stream protection, merge reachability and outbox worker validation.

Verification:

```text
Documentation-only change.
```

Next:

- Wait for user black-box validation feedback before moving to P4.

### 2026-08-25: P4 Task 1 Workflow Persistence and Start-work Pinning

Scope:

- Added current P4 implementation plan: `docs/superpowers/plans/2026-08-25-agora-p4-workflow-harness.md`.
- Added WorkflowDefinition, immutable WorkflowVersion, WorkflowExecution and WorkflowStepRun schema.
- Added built-in `standard-ai-development` workflow with analysis, design, review, implementation, self_test and delivery.
- `agora_start_work` now ensures one authoritative WorkflowExecution per WorkItem, creates step runs, pins WorkflowVersion to WorkSession and returns `workflow_version_id`.
- WorkItem API projections now include workflow execution state and step runs.
- New WorkItems start at workflow stage `analysis` instead of `backlog`.
- Existing P0 e2e fake core now accepts workflow-pinned WorkSessions so old black-box loop coverage stays active.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/api/test_harness_api.py::test_start_work_endpoint_returns_session tests/integration/api/test_work_items_api.py::test_start_work_creates_listable_work_item_for_authorized_project
# 3 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/harness/test_harness_service.py tests/integration/test_migrations.py
# 33 passed

.venv/bin/pytest tests/e2e/test_p0_loop.py::test_p0_loop
# 1 passed

.venv/bin/pytest
# 189 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Next:

- Add canonical `agora_complete_workflow_step` with prerequisite and role checks.

### 2026-08-25: P4 Task 2 Canonical Workflow Step Completion

Scope:

- Added `agora_complete_workflow_step` to the MCP tool facade so AI tools can advance the workflow through Agora instead of calling ad hoc helpers.
- Added `/harness/complete-workflow-step` as the canonical API endpoint.
- Reused project-session membership enforcement before workflow advancement.
- Workflow execution now rejects non-current step completion with `WORKFLOW_STEP_NOT_CURRENT`.
- Completing a step marks it `completed`, moves the next step to `running`, synchronizes WorkItem `stage` and records a `workflow_step_completed` event with actor and summary metadata.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_complete_workflow_step_advances_current_step_and_work_item_stage tests/integration/api/test_harness_api.py::test_complete_workflow_step_rejects_non_current_step
# failed first with 404 before implementation, then 2 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_delegates_to_harness
# failed first with missing agora_complete_workflow_step, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/unit/harness/test_harness_service.py
# 34 passed

.venv/bin/pytest
# 192 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Next:

- Add WorkArtifact and HumanConfirmation capture so required step outputs and human-in-the-loop review evidence become first-class audit records.

### 2026-08-25: P4 Task 3 Work Artifacts and Human Confirmations

Scope:

- Added `work_artifacts` and `human_confirmations` schema in migration `20260825_0006`.
- Added WorkArtifact and HumanConfirmation ORM models linked to WorkItem, WorkSession, WorkflowExecution and WorkflowStepRun.
- Extended `agora_complete_workflow_step` to accept fixed step output artifacts and human confirmation payloads.
- The API/MCP response now returns created artifact and confirmation IDs so AI tools can cite the durable audit records.
- `workflow_step_completed` events now include artifact IDs and human confirmation ID.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first before 0006 migration, then 3 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py::test_complete_workflow_step_captures_artifacts_and_human_confirmation
# failed first before models existed, then 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_delegates_to_harness tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_passes_artifacts_and_human_confirmation
# failed first before MCP accepted artifacts, then 2 passed

.venv/bin/pytest tests/integration/test_migrations.py tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/unit/harness/test_harness_service.py
# 43 passed

.venv/bin/pytest
# 194 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Next:

- Extend Web WorkItem detail so project managers, QA and developers can inspect workflow steps, artifacts and confirmations without calling APIs.

### 2026-08-26: P4 Task 4 Web Workflow Audit Detail

Scope:

- Added read projections for WorkArtifact and HumanConfirmation records by WorkflowExecution.
- WorkItem detail API now includes per-step `artifacts` and `human_confirmations`.
- WorkItem detail Web page now renders a `Workflow audit` section with step status, required outputs, submitted step outputs and human confirmations.
- Verified the page through a production-style local API/Web SSR request with human/agent bearer tokens and a temporary SQLite database.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_work_items_api.py::test_work_item_detail_includes_workflow_artifacts_and_confirmations
# failed first before API returned artifacts, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_work_item_detail_page_renders_workflow_audit_evidence
# failed first before page rendered Workflow audit, then 1 passed

.venv/bin/pytest tests/integration/api/test_work_items_api.py tests/integration/api/test_harness_api.py tests/integration/test_web_config.py tests/unit/harness/test_harness_service.py
# 38 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest
# 196 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

Production-style local SSR check:
# API: 127.0.0.1:18110, Web: 127.0.0.1:13110, temporary database /tmp/agora-p4-web-audit.db
# HTML contained Workflow audit, Step outputs, Human confirmations, AG-888 分析记录 and 人工确认文本.

git diff --check
# passed
```

Next:

- Add the P4 black-box validation guide and then hand the whole P4 workflow audit flow to the user for browser validation.

### 2026-08-26: P4 Task 5 Black-box Validation Guide

Scope:

- Added `docs/development/p4-workflow-audit-blackbox.zh-CN.md`.
- The guide covers production-style local service startup, real AI-tool `agora_start_work`, workflow step completion through `agora_complete_workflow_step`, Web WorkItem workflow audit review and jump-protection validation.
- The guide explicitly keeps user validation at the AI tool/Web level and does not require manual HTTP API calls.
- Added a regression check to keep the P4 black-box guide and key acceptance points in the repo.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_p4_workflow_audit_blackbox_guide_exists
# 1 passed

.venv/bin/pytest tests/integration/test_web_config.py
# 9 passed

.venv/bin/pytest
# 197 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Next:

- Wait for user black-box validation feedback before moving to P5.

### 2026-08-26: P5 Task 1-2 SkillVersion Pins and AI-tool SkillCandidate Submission

Scope:

- Added current P5 implementation plan: `docs/superpowers/plans/2026-08-26-agora-p5-skill-governance.md`.
- Added immutable `skill_versions` schema and pins from logical Skill to current approved version.
- Skill approval now creates or reuses an approved immutable SkillVersion.
- Skill runs and WorkSessions now record `skill_version_id`, so historical work is tied to the exact team capability used.
- Skills API and Web now expose current SkillVersion metadata, and WorkItem capability projections include SkillVersion pins.
- Added canonical AI-tool submission path for SkillCandidates from a real WorkSession through `/harness/submit-skill-candidate` and `agora_submit_skill_candidate`.
- SkillCandidate submissions preserve WorkItem/session provenance, triggers, instructions and WorkArtifact evidence IDs, record a session audit event, and return the next human review action.
- Skill review payloads can now show WorkArtifact evidence references in addition to legacy source assets.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first before 0007 migration and SkillVersion schema, then 3 passed

.venv/bin/pytest tests/integration/api/test_skills_api.py::test_approving_and_running_skill_creates_and_pins_immutable_skill_version
# failed first before SkillVersionModel and pins existed, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_skills_page_renders_current_skill_version
# failed first before Web rendered current version, then passed in grouped verification

.venv/bin/pytest tests/integration/api/test_harness_api.py::test_submit_skill_candidate_from_work_session_creates_reviewable_project_skill
# failed first with route not found, then 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_submit_skill_candidate_delegates_to_harness
# failed first with missing agora_submit_skill_candidate, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_skills_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/integration/test_migrations.py tests/integration/test_web_config.py tests/unit/harness/test_skill_runner.py
# 52 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest tests/integration/test_p2_migration.py
# 16 passed after fixing the legacy P1 migration test fixture to create a real Alembic 0001 schema before dropping alembic_version

.venv/bin/pytest
# 201 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Black-box path:

- Not handed to the user yet. P5 black-box verification should wait until the complete submit-review-publish-reuse loop is implemented, so the user can validate a meaningful end-to-end capability instead of a tiny partial step.

Next:

- Add reviewer edit-and-approve flow that publishes a new immutable SkillVersion from a SkillCandidate.
- Make ContextPlanner/Harness select only approved applicable SkillVersions and include them in the task ContextBundle.

### 2026-08-26: P5 Task 3 SkillCandidate Review Publish and SkillVersion Reuse

Scope:

- Human reviewers can now edit Skill name, version, summary, triggers, schemas, instructions and risk constraints while approving a SkillCandidate.
- Approval preserves AI-submitted provenance and WorkArtifact evidence, then publishes an immutable approved SkillVersion.
- SkillVersion definitions now include logical Skill slug/name so AI tools can consume the version directly from a ContextBundle.
- `agora_prepare_context` now selects project-scoped approved SkillVersions by trigger match and returns them in `skills`.
- ContextBundle `capability_pins` now includes `skill_version_ids` and the first `skill_version_id` for compatibility with existing single-pin views.
- Web Skills page now includes a `Publish approved version` form so reviewer edits and approval can happen through the browser.
- Added `docs/development/p5-skill-governance-blackbox.zh-CN.md` for the full AI-tool submit, Web review publish and later AI-tool reuse flow.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_skills_api.py::test_reviewer_can_publish_candidate_skill_version_with_review_edits
# failed first because approve ignored reviewer edits, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py::test_prepare_context_returns_applicable_approved_skill_versions_for_ai_tool
# failed first because ContextBundle had no skill_version_ids, then failed once more due overly broad slug matching, then 1 passed after trigger-only matching for triggered Skills

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_skills_api.py tests/unit/harness/test_harness_service.py tests/unit/harness/test_context_bundle.py tests/unit/mcp/test_tools.py tests/integration/test_web_config.py
# 55 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest
# 204 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Black-box path:

- `docs/development/p5-skill-governance-blackbox.zh-CN.md`
- This can now be handed to the user after final full verification for browser/AI-tool validation.

Next:

- Run full verification and commit.
- Continue P5 with duplicate detection and repeated-experience suggestions if the user wants more development before black-box validation.

### 2026-08-26: P5 Task 4 Duplicate Detection and Repeated-experience Suggestions

Scope:

- `agora_submit_skill_candidate` now merges duplicate candidate/draft Skills by same project and slug instead of creating multiple review items.
- Duplicate merging preserves and de-duplicates triggers and evidence artifact ids.
- Duplicate submissions return `deduplicated=true`, so the AI tool can tell the user the candidate was merged into an existing review item.
- Added `agora_suggest_skills` Harness/API/MCP capability to derive reusable Skill suggestions from repeated project WorkArtifacts.
- Registered `agora_submit_skill_candidate` and `agora_suggest_skills` in the stdio MCP server for real AI-tool testing.
- Updated P5 black-box guide to cover automatic suggestion, duplicate merging, Web review publish and later AI-tool reuse.
- P5 is now implementation-complete for black-box validation.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_submit_skill_candidate_merges_duplicate_slug_into_existing_candidate
# failed first because duplicate submissions created a second Skill, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py::test_ai_tool_gets_repeated_experience_skill_suggestions_from_work_artifacts
# failed first because /harness/suggest-skills did not exist, then 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_suggest_skills_delegates_to_harness tests/unit/mcp/test_stdio_server.py::test_stdio_mcp_server_lists_agora_tools tests/unit/mcp/test_stdio_server.py::test_stdio_submit_skill_candidate_dispatches_to_harness tests/unit/mcp/test_stdio_server.py::test_stdio_suggest_skills_dispatches_to_harness
# stdio submit registration failed first, then 4 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_skills_api.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/unit/harness/test_context_bundle.py tests/unit/harness/test_harness_service.py tests/integration/test_web_config.py
# 65 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest
# 209 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

Black-box path:

- `docs/development/p5-skill-governance-blackbox.zh-CN.md`

Next:

- Run final full verification and commit.
- Hand P5 black-box validation steps to the user.
