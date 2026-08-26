# Agora P5 Skill and Team Memory Governance Implementation Plan

**Goal:** Turn approved team methods and repeated project experience into versioned, reusable AI work capabilities.

This is the current realigned P5 plan. The older `2026-08-13-agora-p5-session-audit.md` remains historical implementation evidence for session audit, but it is not the canonical P5 scope after the product realignment.

## Task 1: SkillVersion foundation and usage pinning

**Files:**

- Create: `alembic/versions/20260826_0007_p5_skill_versions.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/skills.py`
- Modify: `packages/core/repositories/work.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/skill_orchestrator.py`
- Modify: `apps/api/routers/skills.py`
- Modify: `apps/api/routers/work_items.py`
- Modify: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Test: `tests/integration/test_migrations.py`
- Test: `tests/integration/api/test_skills_api.py`
- Test: `tests/integration/test_web_config.py`
- Test: `tests/unit/harness/test_skill_runner.py`

- [x] Add immutable `skill_versions` schema linked to logical `skills`.
- [x] Pin `skills.current_version_id` after approval.
- [x] Pin `skill_runs.skill_version_id` when an approved Skill is executed.
- [x] Pin `work_sessions.skill_version_id` so historical work remains tied to the exact capability used.
- [x] Return current version metadata in Skills API and Web.
- [x] Include SkillVersion pins in WorkItem capability projections.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first before 0007 migration and SkillVersion schema, then 3 passed

.venv/bin/pytest tests/integration/api/test_skills_api.py::test_approving_and_running_skill_creates_and_pins_immutable_skill_version
# failed first before SkillVersionModel and pins existed, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_skills_page_renders_current_skill_version
# failed first before Web rendered the current version, then passed in grouped verification

.venv/bin/pytest tests/integration/api/test_skills_api.py tests/integration/api/test_work_items_api.py tests/integration/test_migrations.py tests/integration/test_web_config.py tests/unit/harness/test_skill_runner.py
# 29 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

## Task 2: AI-tool SkillCandidate submission from real work

**Files:**

- Modify: `packages/core/repositories/workflows.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/api/routers/skills.py`
- Modify: `apps/mcp/tools.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/unit/mcp/test_tools.py`

- [x] Add canonical Harness/API operation for an AI tool to submit a SkillCandidate from a WorkSession.
- [x] Add MCP facade `agora_submit_skill_candidate`.
- [x] Preserve candidate provenance: session, WorkItem, submitting user, triggers, instructions and evidence artifact IDs.
- [x] Record a `skill_candidate_submitted` WorkSession event for audit.
- [x] Return the next action `human_review_skill_candidate`, keeping publish approval human-governed.
- [x] Show WorkArtifact evidence references on the Skills review page.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_submit_skill_candidate_from_work_session_creates_reviewable_project_skill
# failed first with route not found, then 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_submit_skill_candidate_delegates_to_harness
# failed first with missing agora_submit_skill_candidate, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_skills_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/integration/test_migrations.py tests/integration/test_web_config.py tests/unit/harness/test_skill_runner.py
# 52 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest tests/integration/test_p2_migration.py
# 16 passed after fixing the legacy P1 test fixture to use Alembic 0001 schema instead of current ORM create_all

.venv/bin/pytest
# 201 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

## Next P5 tasks

- [x] Add reviewer edit-and-approve flow that publishes a new immutable SkillVersion from a SkillCandidate.
- [x] Make ContextPlanner/Harness select only approved applicable SkillVersions and include them in the task ContextBundle.
- Add duplicate detection and repeated-experience suggestions from accepted artifacts and completed WorkSessions.
- [x] Prepare the P5 black-box guide after the full submit-review-publish-reuse loop is available.

## Task 3: Human review publish and AI-tool SkillVersion reuse

**Files:**

- Modify: `packages/core/repositories/skills.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/context_bundle.py`
- Modify: `packages/harness/context_planner.py`
- Modify: `apps/api/routers/skills.py`
- Modify: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/skills/[skillId]/approve/route.ts`
- Create: `docs/development/p5-skill-governance-blackbox.zh-CN.md`
- Test: `tests/integration/api/test_skills_api.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/integration/test_web_config.py`

- [x] Allow human reviewers to edit Skill name, version, triggers, summary, schemas, instructions and risk constraints while approving a SkillCandidate.
- [x] Preserve AI-submitted provenance and WorkArtifact evidence when the reviewer publishes the approved SkillVersion.
- [x] Store immutable SkillVersion definitions with logical Skill slug/name for AI-tool consumption.
- [x] Add project-scoped applicable SkillVersion selection by triggers for `prepare_context`.
- [x] Include applicable SkillVersions in ContextBundle `skills` and pin them in `capability_pins.skill_version_ids`.
- [x] Add Web `Publish approved version` form so black-box validation can happen in the browser.
- [x] Add P5 black-box guide for the full submit-review-publish-reuse loop.

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

## Remaining P5 tasks

- [x] Add duplicate detection and repeated-experience suggestions from accepted artifacts and completed WorkSessions.
- [x] Keep reviewer ergonomics sufficient for P5 black-box through the Web `Publish approved version` form; defer richer visual diff until the review UI becomes the next bottleneck.

## Task 4: Duplicate detection and repeated-experience suggestions

**Files:**

- Modify: `packages/core/repositories/workflows.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/tools.py`
- Modify: `apps/mcp/server.py`
- Modify: `docs/development/p5-skill-governance-blackbox.zh-CN.md`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/unit/mcp/test_stdio_server.py`
- Test: `tests/integration/test_web_config.py`

- [x] Merge duplicate `agora_submit_skill_candidate` submissions by same project and slug when the existing Skill is still candidate/draft.
- [x] Preserve and merge evidence artifact ids and triggers without duplicating values.
- [x] Return `deduplicated=true` so AI tools can explain that the candidate was merged into an existing review item.
- [x] Add `agora_suggest_skills` Harness/API/MCP capability that derives repeated-experience suggestions from project WorkArtifacts.
- [x] Register both `agora_submit_skill_candidate` and `agora_suggest_skills` in the stdio MCP server for real AI-tool black-box testing.
- [x] Update the P5 black-box guide to cover automatic suggestion and duplicate candidate merging.

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

## P5 status

P5 implementation scope is complete enough for black-box validation:

- AI tools can submit SkillCandidates from real work.
- Duplicate candidates merge into one review item.
- Agora can suggest reusable Skills from repeated WorkArtifacts.
- Humans can publish immutable SkillVersions in Web.
- Later AI tasks receive approved SkillVersions through `agora_prepare_context`.
- Historical runs and sessions retain SkillVersion pins.
