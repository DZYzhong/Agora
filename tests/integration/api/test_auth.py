import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api import main as api_main
from apps.api.main import app
from packages.core.settings import RuntimeConfigurationError
from packages.core.models import AssetModel, ProjectModel, TaskSessionModel
from packages.core.uow import SqlAlchemyUnitOfWork

HUMAN_TOKEN = "test-human-token-secret-value"
AGENT_TOKEN = "test-agent-token-secret-value"
CI_TOKEN = "test-ci-token-secret-value"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _production_auth(monkeypatch, *, org_id: str | None = "local-org") -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", CI_TOKEN)
    if org_id is None:
        monkeypatch.delenv("AGORA_BOOTSTRAP_ORG_ID", raising=False)
    else:
        monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", org_id)


def _create_unowned_project_and_session():
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            project = ProjectModel(org_id="foreign-org", name="Foreign", slug="foreign")
            db.add(project)
            db.flush()
            task_session = TaskSessionModel(
                org_id=project.org_id,
                project_id=project.id,
                agent_type="codex",
                intent="foreign work",
            )
            db.add(task_session)
            asset = AssetModel(
                org_id=project.org_id,
                project_id=project.id,
                type="document",
                source="test",
                source_uri="foreign.md",
                title="Foreign",
                content="foreign content",
            )
            db.add(asset)
            db.flush()
            ids = project.id, task_session.id, asset.id
            uow.commit()
            return ids
    finally:
        db.close()


def test_lifespan_startup_refuses_production_auth_bypass_before_bootstrap(monkeypatch):
    monkeypatch.setenv("AGORA_ENV", "production")
    monkeypatch.setenv("AGORA_TEST_AUTH_BYPASS", "1")
    monkeypatch.setenv("AGORA_DATABASE_URL", "postgresql://user:secret@database/agora")
    monkeypatch.setattr(
        api_main,
        "bootstrap_auth_from_env",
        lambda: pytest.fail("auth bootstrap ran before runtime policy validation"),
    )

    with pytest.raises(RuntimeConfigurationError) as exc:
        with TestClient(app):
            pass

    assert exc.value.code == "AGORA_TEST_AUTH_BYPASS_FORBIDDEN"


def test_lifespan_startup_refuses_production_local_init_root_before_bootstrap(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("AGORA_ENV", "production")
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_DATABASE_URL", "postgresql://user:secret@database/agora")
    monkeypatch.setenv("AGORA_LOCAL_INIT_ROOT", str(tmp_path / "local-init"))
    monkeypatch.setattr(
        api_main,
        "bootstrap_auth_from_env",
        lambda: pytest.fail("auth bootstrap ran before runtime policy validation"),
    )

    with pytest.raises(RuntimeConfigurationError) as exc:
        with TestClient(app):
            pass

    assert exc.value.code == "AGORA_LOCAL_INIT_ROOT_FORBIDDEN"


def test_missing_and_invalid_bearer_tokens_return_stable_auth_errors(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        missing = client.get("/projects")
        invalid = client.get("/projects", headers=_auth_headers("wrong-token"))

    assert missing.status_code == 401
    assert missing.json()["detail"]["code"] == "AUTH_REQUIRED"
    assert invalid.status_code == 401
    assert invalid.json()["detail"]["code"] == "INVALID_CREDENTIAL"


def test_human_and_agent_tokens_have_separate_boundaries_and_payload_org_cannot_override(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        created = client.post(
            "/projects",
            headers=_auth_headers(HUMAN_TOKEN),
            json={
                "org_id": "attacker-org",
                "name": "Owned",
                "slug": "owned",
                "git_remotes": [],
            },
        )
        agent_create = client.post(
            "/projects",
            headers=_auth_headers(AGENT_TOKEN),
            json={
                "org_id": "local-org",
                "name": "Agent Project",
                "slug": "agent-project",
                "git_remotes": [],
            },
        )

    assert created.status_code == 201
    assert created.json()["org_id"] == "local-org"
    assert agent_create.status_code == 403
    assert agent_create.json()["detail"]["code"] == "HUMAN_CREDENTIAL_REQUIRED"


def test_ci_bootstrap_token_is_service_scoped_and_cannot_create_projects(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_auth_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "CI Token Scope",
                "slug": "ci-token-scope",
                "git_remotes": [],
            },
        )
        ci_create = client.post(
            "/projects",
            headers=_auth_headers(CI_TOKEN),
            json={
                "org_id": "local-org",
                "name": "CI Project",
                "slug": "ci-project",
                "git_remotes": [],
            },
        )

    assert project.status_code == 201
    assert ci_create.status_code == 403
    assert ci_create.json()["detail"]["code"] == "HUMAN_CREDENTIAL_REQUIRED"


def test_non_member_cannot_read_or_start_work_in_project(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project_id, _, _ = _create_unowned_project_and_session()
        read = client.get(f"/projects/{project_id}", headers=_auth_headers(HUMAN_TOKEN))
        start = client.post(
            "/harness/start-work",
            headers=_auth_headers(AGENT_TOKEN),
            json={
                "project_id": project_id,
                "user_message": "start foreign work",
                "agent_type": "codex",
            },
        )

    assert read.status_code == 404
    assert start.status_code == 404


def test_non_member_start_work_vague_message_does_not_leak_foreign_project(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project_id, _, _ = _create_unowned_project_and_session()
        db = sessionmaker(bind=get_engine())()
        try:
            project = db.get(ProjectModel, project_id)
            remote = "git@example.com:foreign.git"
            project.git_remotes = [remote]
            db.commit()
        finally:
            db.close()

        response = client.post(
            "/harness/start-work",
            headers=_auth_headers(AGENT_TOKEN),
            json={
                "repo_remote": remote,
                "user_message": "开始工作",
                "agent_type": "codex",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_session_commands_reject_sessions_outside_principal_membership(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        _, session_id, asset_id = _create_unowned_project_and_session()
        requests = [
            client.post(
                "/harness/plan-context",
                headers=_auth_headers(AGENT_TOKEN),
                json={"session_id": session_id, "query": "foreign", "token_budget": 500},
            ),
            client.post(
                "/harness/fetch-context-ref",
                headers=_auth_headers(AGENT_TOKEN),
                json={"session_id": session_id, "asset_id": asset_id, "max_tokens": 20},
            ),
            client.post(
                "/harness/record-event",
                headers=_auth_headers(AGENT_TOKEN),
                json={"session_id": session_id, "event_type": "note", "payload": {}},
            ),
            client.post(
                "/harness/close-work",
                headers=_auth_headers(AGENT_TOKEN),
                json={"session_id": session_id, "status": "closed"},
            ),
            client.post(
                "/harness/prepare-writeback",
                headers=_auth_headers(AGENT_TOKEN),
                json={
                    "session_id": session_id,
                    "type": "development_summary",
                    "title": "Foreign",
                    "content": "No access",
                    "asset_refs": [],
                },
            ),
        ]

    assert [response.status_code for response in requests] == [404, 404, 404, 404, 404]
