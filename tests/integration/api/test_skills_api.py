from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.models import SkillModel, SkillRunModel
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.uow import SqlAlchemyUnitOfWork


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
