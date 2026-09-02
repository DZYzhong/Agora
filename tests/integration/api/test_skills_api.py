from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.auth import hash_token, token_diagnostic_prefix
from packages.core.models import CredentialModel, SecurityAuditEventModel, SkillModel, SkillRunModel, SkillVersionModel, UserModel, WorkSessionModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.uow import SqlAlchemyUnitOfWork

HUMAN_TOKEN = "skills-human-token"
AGENT_TOKEN = "skills-agent-token"
MEMBER_TOKEN = "skills-member-token"
PROTOCOL_11_HEADERS = {"Agora-Protocol-Version": "1.1", "Agora-Connector-Version": "0.1.0"}


def _idem(key: str) -> dict:
    return {**PROTOCOL_11_HEADERS, "Idempotency-Key": key}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _session_client() -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _csrf_headers(csrf_token: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf_token, "Origin": "http://127.0.0.1:13140"}


def _web_approver(client: TestClient, *, project_id: str, role: str = "owner") -> str:
    from uuid import uuid4

    from packages.core.models import UserModel
    from packages.core.passwords import hash_password

    username = f"web-{uuid4().hex[:10]}"
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            user = UserModel(
                org_id="local-org",
                username=username,
                display_name="Web Approver",
                status="active",
                is_placeholder=False,
                password_hash=hash_password("web-password"),
            )
            db.add(user)
            db.flush()
            IdentityRepository(db).grant_membership(project_id=project_id, user_id=user.id, role=role)
            uow.commit()
    finally:
        db.close()
    login = client.post("/auth/login", json={"username": username, "password": "web-password"})
    assert login.status_code == 200, login.text
    csrf = login.json()["csrf_token"]
    reauth = client.post("/auth/reauth", json={"password": "web-password"}, headers=_csrf_headers(csrf))
    assert reauth.status_code == 200, reauth.text
    return csrf


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def _grant_member(project_id: str, *, token: str = MEMBER_TOKEN, role: str = "member") -> None:
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            user = UserModel(org_id="local-org", display_name=f"{role.title()} User", status="active", is_placeholder=False)
            db.add(user)
            db.flush()
            credential = CredentialModel(
                user_id=user.id,
                kind="human",
                token_hash=hash_token(token),
                token_prefix=token_diagnostic_prefix(token),
                status="active",
            )
            db.add(credential)
            db.flush()
            IdentityRepository(db).grant_membership(project_id=project_id, user_id=user.id, role=role)
            uow.commit()
    finally:
        db.close()


def test_project_skill_lifecycle_and_run_history():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_lifecycle",
            "name": "Skill Lifecycle",
            "slug": "skill-lifecycle",
            "git_remotes": ["git@example.com:skill-lifecycle.git"],
        },
    ).json()

    create_response = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "release-risk-review",
            "name": "Release Risk Review",
            "status": "candidate",
            "definition": {
                "version": "0.1.0",
                "triggers": ["release", "risk"],
                "input_schema": {"type": "object"},
                "instructions": "Review release risk and produce concise findings.",
            },
        },
    )

    assert create_response.status_code == 201
    skill = create_response.json()
    assert skill["status"] == "candidate"
    assert skill["definition"]["version"] == "0.1.0"

    update_response = client.patch(
        f"/projects/{project['id']}/skills/{skill['id']}",
        json={
            "status": "draft",
            "definition": {
                "version": "0.2.0",
                "triggers": ["release", "risk", "rollback"],
                "input_schema": {"type": "object"},
                "instructions": "Review release and rollback risk.",
            },
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "draft"
    assert update_response.json()["definition"]["version"] == "0.2.0"

    approve_response = client.post(f"/projects/{project['id']}/skills/{skill['id']}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    run_response = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={
            "session_id": None,
            "input": {"change": "release payment retry"},
            "context": {"summary": "Payment retry release touches refund flow."},
        },
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["skill_id"] == skill["id"]
    assert run["input"]["change"] == "release payment retry"
    assert run["output"]["summary"]

    runs_response = client.get(f"/projects/{project['id']}/skill-runs")
    assert runs_response.status_code == 200
    runs_before_block = runs_response.json()
    assert len(runs_before_block) == 1
    assert runs_before_block[0]["id"] == run["id"]
    assert runs_before_block[0]["status"] == "completed"

    deprecate_response = client.post(f"/projects/{project['id']}/skills/{skill['id']}/deprecate")
    assert deprecate_response.status_code == 200
    assert deprecate_response.json()["status"] == "deprecated"

    blocked_run = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={
            "input": {"change": "release payment retry"},
            "context": {"summary": "Payment retry release touches refund flow."},
        },
    )
    assert blocked_run.status_code == 400
    assert blocked_run.json()["detail"] == "Skill is not approved: release-risk-review"
    runs_after_block = client.get(f"/projects/{project['id']}/skill-runs").json()
    assert runs_after_block == runs_before_block

    skills = client.get(f"/projects/{project['id']}/skills").json()
    assert any(item["slug"] == "task-context-summary" and item["builtin"] for item in skills)
    assert any(item["slug"] == "release-risk-review" and not item["builtin"] for item in skills)


def test_skill_approval_rejects_agent_and_non_reviewer_member_with_audit(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = client.post(
            "/projects",
            headers=_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "Skill Approval RBAC",
                "slug": "skill-approval-rbac",
                "git_remotes": [],
            },
        ).json()
        skill = client.post(
            f"/projects/{project['id']}/skills",
            headers=_headers(HUMAN_TOKEN),
            json={
                "slug": "security-review",
                "name": "Security Review",
                "status": "candidate",
                "definition": {
                    "version": "1.0.0",
                    "triggers": ["security"],
                    "instructions": "检查权限风险。",
                },
            },
        ).json()
        _grant_member(project["id"], role="member")

        agent_denied = client.post(
            f"/projects/{project['id']}/skills/{skill['id']}/approve",
            headers=_headers(AGENT_TOKEN),
        )
        member_approver = _web_approver(client, project_id=project["id"], role="member")
        member_denied = client.post(
            f"/projects/{project['id']}/skills/{skill['id']}/approve",
            headers=_csrf_headers(member_approver),
        )
        audit_response = client.get(
            f"/projects/{project['id']}/security-audit",
            headers=_headers(HUMAN_TOKEN),
        )

    assert agent_denied.status_code == 403
    assert agent_denied.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"
    assert member_denied.status_code == 403
    assert member_denied.json()["detail"]["code"] == "PROJECT_ROLE_REQUIRED"
    assert audit_response.status_code == 200
    assert [event["decision"] for event in audit_response.json()[-2:]] == ["deny", "deny"]
    assert {event["reason"] for event in audit_response.json()[-2:]} == {"APPROVAL_CREDENTIAL_REQUIRED", "PROJECT_ROLE_REQUIRED"}

    with sessionmaker(bind=get_engine())() as db:
        events = db.query(SecurityAuditEventModel).filter_by(project_id=project["id"]).order_by(SecurityAuditEventModel.created_at).all()
        assert [event.action for event in events[-2:]] == ["skill.approve", "skill.approve"]
        assert [event.decision for event in events[-2:]] == ["deny", "deny"]
        assert {event.reason for event in events[-2:]} == {"APPROVAL_CREDENTIAL_REQUIRED", "PROJECT_ROLE_REQUIRED"}


def test_approving_and_running_skill_creates_and_pins_immutable_skill_version():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_versions",
            "name": "Skill Versions",
            "slug": "skill-versions",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-501：复用发布风险检查经验",
            "agent_type": "codex",
        },
    ).json()
    skill = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "release-risk-review",
            "name": "Release Risk Review",
            "status": "candidate",
            "definition": {
                "version": "1.0.0",
                "triggers": ["release", "risk"],
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "instructions": "检查发布风险、回滚方案和测试证据。",
                "risk_constraints": ["不要把缺失测试说成通过"],
            },
        },
    ).json()

    approved = client.post(f"/projects/{project['id']}/skills/{skill['id']}/approve").json()

    assert approved["status"] == "approved"
    assert approved["current_version"]["version"] == "1.0.0"
    assert approved["current_version"]["status"] == "approved"
    version_id = approved["current_version"]["id"]

    run_response = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={
            "session_id": started["session_id"],
            "input": {"change": "支付导出权限审计发布"},
            "context": {"summary": "本次发布涉及权限审计和导出限流。"},
        },
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["skill_version_id"] == version_id

    with sessionmaker(bind=get_engine())() as session:
        version = session.get(SkillVersionModel, version_id)
        skill_run = session.get(SkillRunModel, run["id"])
        work_session = session.get(WorkSessionModel, started["session_id"])
        assert version.skill_id == skill["id"]
        assert version.definition["instructions"] == "检查发布风险、回滚方案和测试证据。"
        assert skill_run.skill_version_id == version_id
        assert work_session.skill_version_id == version_id


def test_reviewer_can_publish_candidate_skill_version_with_review_edits():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_review_publish",
            "name": "Skill Review Publish",
            "slug": "skill-review-publish",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-701：沉淀发布检查经验",
            "agent_type": "codex",
        },
    ).json()
    completed = client.post(
        "/harness/complete-workflow-step",
        headers=_idem("key-skill-complete"),
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "完成候选 skill 证据整理。",
            "artifacts": [
                {
                    "type": "analysis_note",
                    "title": "AG-701 发布检查经验",
                    "content": "发布检查要覆盖风险说明、测试证据、回滚方案和监控。",
                }
            ],
        },
    ).json()
    submitted = client.post(
        "/harness/submit-skill-candidate",
        json={
            "session_id": started["session_id"],
            "slug": "release-readiness-review",
            "name": "Release Readiness Review",
            "summary": "AI 工具提交的初稿。",
            "triggers": ["release"],
            "instructions": "初稿：检查发布风险。",
            "artifact_ids": [completed["artifacts"][0]["id"]],
        },
    ).json()

    approve_response = client.post(
        f"/projects/{project['id']}/skills/{submitted['skill']['id']}/approve",
        json={
            "name": "Release Readiness Review",
            "definition": {
                "version": "1.0.0",
                "summary": "发布前检查团队标准流程。",
                "triggers": ["release", "rollback", "monitoring"],
                "input_schema": {"type": "object", "required": ["change_summary"]},
                "output_schema": {"type": "object"},
                "instructions": "检查风险说明、测试证据、回滚方案、监控和负责人。",
                "risk_constraints": ["缺少测试证据时必须标记为风险"],
            },
        },
    )

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "approved"
    assert approved["name"] == "Release Readiness Review"
    assert approved["definition"]["instructions"] == "检查风险说明、测试证据、回滚方案、监控和负责人。"
    assert approved["definition"]["evidence_artifact_ids"] == [completed["artifacts"][0]["id"]]
    assert approved["current_version"]["version"] == "1.0.0"
    assert approved["current_version"]["definition"]["triggers"] == ["release", "rollback", "monitoring"]
    assert approved["current_version"]["definition"]["risk_constraints"] == ["缺少测试证据时必须标记为风险"]
    assert approved["evidence_refs"][0]["title"] == "AG-701 发布检查经验"


def test_repeated_accepted_writebacks_create_candidate_skill():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_candidates",
            "name": "Skill Candidates",
            "slug": "skill-candidates",
            "git_remotes": ["git@example.com:skill-candidates.git"],
        },
    ).json()
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "分析发布风险",
            "agent_type": "codex",
        },
    ).json()

    for index in range(2):
        writeback = client.post(
            "/harness/prepare-writeback",
            json={
                "session_id": start["session_id"],
                "type": "release_risk_review",
                "title": f"Release risk review {index}",
                "content": "Review release risk, rollback path, and test evidence before deployment.",
                "asset_refs": [],
            },
        ).json()
        accept = client.post(f"/projects/{project['id']}/writebacks/{writeback['id']}/accept")
        assert accept.status_code == 200

    skills = client.get(f"/projects/{project['id']}/skills").json()
    candidate = next(item for item in skills if item["slug"] == "release-risk-review")
    assert candidate["status"] == "candidate"
    assert not candidate["builtin"]
    assert candidate["definition"]["source"] == "accepted_writebacks"
    assert candidate["definition"]["writeback_type"] == "release_risk_review"
    assert [item["title"] for item in candidate["evidence_refs"]] == [
        "Release risk review 0",
        "Release risk review 1",
    ]
    assert all(item["status"] == "accepted" for item in candidate["evidence_refs"])
    assert all(item["content_preview"].startswith("Review release risk") for item in candidate["evidence_refs"])


def test_builtin_skills_are_read_only_for_lifecycle_updates():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_builtin_read_only",
            "name": "Built-in Read Only",
            "slug": "builtin-read-only",
            "git_remotes": ["git@example.com:builtin-read-only.git"],
        },
    ).json()
    skills = client.get(f"/projects/{project['id']}/skills").json()
    builtin = next(item for item in skills if item["slug"] == "task-context-summary")

    update_response = client.patch(
        f"/projects/{project['id']}/skills/{builtin['id']}",
        json={"status": "deprecated"},
    )
    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Built-in skills are read-only"

    deprecate_response = client.post(f"/projects/{project['id']}/skills/{builtin['id']}/deprecate")
    assert deprecate_response.status_code == 400
    assert deprecate_response.json()["detail"] == "Built-in skills are read-only"

    refreshed = client.get(f"/projects/{project['id']}/skills").json()
    refreshed_builtin = next(item for item in refreshed if item["id"] == builtin["id"])
    assert refreshed_builtin["status"] == "approved"


def test_failed_skill_audit_write_failure_preserves_original_business_error(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_audit_failure",
            "name": "Skill Audit Failure",
            "slug": "skill-audit-failure",
            "git_remotes": [],
        },
    ).json()
    skill = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "audit-failure-skill",
            "name": "Audit Failure Skill",
            "status": "approved",
            "definition": {"instructions": "Run atomically."},
        },
    ).json()
    original_create_run = SkillRepository.create_run
    calls = 0

    def fail_execution_then_audit(self, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            original_create_run(self, **kwargs)
            raise ValueError("expected execution failure")
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(SkillRepository, "create_run", fail_execution_then_audit)

    response = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={"input": {"change": "audit"}, "context": {"summary": "Preserve original."}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "expected execution failure"
    with sessionmaker(bind=get_engine())() as session:
        assert session.scalar(select(func.count()).select_from(SkillRunModel)) == 0


def test_startup_bootstrap_seeds_builtin_skills_for_existing_projects_without_get_mutation():
    with sessionmaker(bind=get_engine())() as session:
        with SqlAlchemyUnitOfWork(session) as uow:
            project = ProjectRepository(session).create(
                org_id="org_existing_bootstrap",
                name="Existing Bootstrap",
                slug="existing-bootstrap",
                git_remotes=[],
            )
            project_id = project.id
            uow.commit()
        with SqlAlchemyUnitOfWork(session) as uow:
            for skill in list(session.scalars(select(SkillModel)).all()):
                session.delete(skill)
            uow.commit()

    assert TestClient(app).get(f"/projects/{project_id}/skills").json() == []

    with TestClient(app) as client:
        skills = client.get(f"/projects/{project_id}/skills").json()

    assert any(skill["slug"] == "task-context-summary" and skill["builtin"] for skill in skills)
    count_after_bootstrap = len(skills)

    client = TestClient(app)
    before_get_count = client.get(f"/projects/{project_id}/skills").json()
    after_get_count = client.get(f"/projects/{project_id}/skills").json()
    assert len(before_get_count) == count_after_bootstrap
    assert len(after_get_count) == count_after_bootstrap
