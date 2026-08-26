# Agora P7 Governance and Security Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Agora's local-team identity boundary into role-based governance for approvals and sensitive audit.

**Architecture:** Build on the existing User, Credential and ProjectMembership model instead of adding SSO first. Add role checks at approval boundaries and a durable security audit log for sensitive decisions. Keep AI tools able to submit evidence and proposals, but prevent agent credentials or unprivileged project members from approving governed team knowledge.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite/Postgres-compatible migrations, existing Harness/MCP/Web stack.

---

## Chunk 1: Approval RBAC and Security Audit

### Task 1: Schema and repository

**Files:**

- Create: `alembic/versions/20260826_0009_p7_security_audit.py`
- Create: `packages/core/repositories/security.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/test_migrations.py`

- [x] Add `security_audit_events` with actor, credential kind, action, target, decision, reason and metadata.
- [x] Add runtime helpers to record/list security audit events.
- [x] Verify current Alembic head includes the P7 table.

### Task 2: Role checks

**Files:**

- Modify: `packages/core/auth.py`
- Modify: `apps/api/auth.py`
- Modify: `apps/api/routers/context_governance.py`
- Modify: `apps/api/routers/skills.py`
- Test: `tests/integration/api/test_auth.py`
- Test: `tests/integration/api/test_context_governance_api.py`
- Test: `tests/integration/api/test_skills_api.py`

- [x] Add project role helpers: owner/admin/reviewer can approve governed knowledge.
- [x] Reject agent credentials from approval endpoints with stable code `HUMAN_CREDENTIAL_REQUIRED`.
- [x] Reject human members without approval roles with stable code `PROJECT_ROLE_REQUIRED`.
- [x] Record security audit events for allow and deny decisions.

### Task 3: Web audit visibility and black-box guide

**Files:**

- Create: `apps/web/app/projects/[projectId]/security/page.tsx`
- Create: `docs/development/p7-governance-security-blackbox.zh-CN.md`
- Modify: `apps/api/routers/projects.py`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Test: `tests/integration/test_web_config.py`

- [x] Add project-scoped security audit API.
- [x] Add Web security page linked from project home.
- [x] Add black-box guide covering agent deny, reviewer allow and audit visibility.

## Execution Notes

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_p7_security_audit_schema_links_actor_and_project
# failed first because security_audit_events did not exist, then passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py::test_context_approval_rejects_agent_and_non_reviewer_member_with_audit
# failed first because SecurityAuditEventModel did not exist, then passed

.venv/bin/pytest tests/integration/api/test_skills_api.py::test_skill_approval_rejects_agent_and_non_reviewer_member_with_audit
# failed first because SecurityAuditEventModel did not exist, then passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p7_security_audit_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p7_governance_security_blackbox_guide_exists
# failed first because Web page and guide did not exist, then passed
```

### Verification

Run:

```bash
.venv/bin/pytest tests/integration/test_migrations.py tests/integration/api/test_auth.py tests/integration/api/test_context_governance_api.py tests/integration/api/test_skills_api.py tests/integration/test_web_config.py
.venv/bin/pytest
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
git diff --check
```
