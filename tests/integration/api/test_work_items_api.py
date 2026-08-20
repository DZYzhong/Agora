from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.auth import hash_token
from packages.core.models import CredentialModel, ProjectModel, WorkItemModel, WorkSessionModel
from packages.core.uow import SqlAlchemyUnitOfWork

HUMAN_TOKEN = "test-human-token-secret-value"
AGENT_TOKEN = "test-agent-token-secret-value"


def _auth_headers(token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    return headers


def _production_auth(monkeypatch, *, org_id: str = "local-org") -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", org_id)


def test_start_work_creates_listable_work_item_for_authorized_project():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_work_items",
            "name": "Work Items",
            "slug": "work-items",
            "git_remotes": ["git@example.com:work-items.git"],
        },
    ).json()

    started = client.post(
        "/harness/start-work",
        headers={"Idempotency-Key": "work-item-create-1"},
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-128：实现支付状态流转",
            "agent_type": "codex",
        },
    ).json()
    response = client.get(f"/projects/{project['id']}/work-items")

    assert response.status_code == 200
    work_items = response.json()
    assert work_items == [
        {
            "id": started["work_item_id"],
            "project_id": project["id"],
            "external_key": "AG-128",
            "title": "实现支付状态流转",
            "status": "active",
            "stage": "backlog",
            "source": "manual",
            "session_count": 1,
        }
    ]


def test_work_items_are_scoped_to_project_membership(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        owned = client.post(
            "/projects",
            headers=_auth_headers(HUMAN_TOKEN),
            json={
                "org_id": "attacker-org",
                "name": "Owned Work",
                "slug": "owned-work",
                "git_remotes": [],
            },
        ).json()
        db = sessionmaker(bind=get_engine())()
        try:
            with SqlAlchemyUnitOfWork(db) as uow:
                foreign = ProjectModel(org_id="foreign-org", name="Foreign Work", slug="foreign-work")
                db.add(foreign)
                db.flush()
                db.add(
                    WorkItemModel(
                        org_id=foreign.org_id,
                        project_id=foreign.id,
                        title="Foreign task",
                    )
                )
                db.flush()
                foreign_id = foreign.id
                uow.commit()
        finally:
            db.close()

        owned_response = client.get(f"/projects/{owned['id']}/work-items", headers=_auth_headers(HUMAN_TOKEN))
        foreign_response = client.get(f"/projects/{foreign_id}/work-items", headers=_auth_headers(HUMAN_TOKEN))

    assert owned_response.status_code == 200
    assert foreign_response.status_code == 404


def test_work_session_identity_comes_from_authenticated_principal_not_payload(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_auth_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "Principal Identity",
                "slug": "principal-identity",
                "git_remotes": [],
            },
        ).json()
        response = client.post(
            "/harness/start-work",
            headers=_auth_headers(AGENT_TOKEN, {"Idempotency-Key": "principal-identity-1"}),
            json={
                "project_id": project["id"],
                "user_message": "实现认证身份隔离",
                "agent_type": "codex",
                "user_id": "payload-user",
                "credential_id": "payload-credential",
            },
        )

    assert response.status_code == 200
    body = response.json()

    db = sessionmaker(bind=get_engine())()
    try:
        work_session = db.get(WorkSessionModel, body["session_id"])
        agent_credential = db.scalars(
            select(CredentialModel).where(CredentialModel.token_hash == hash_token(AGENT_TOKEN))
        ).one()
        assert work_session.user_id == agent_credential.user_id
        assert work_session.credential_id == agent_credential.id
        assert work_session.user_id != "payload-user"
        assert work_session.credential_id != "payload-credential"
    finally:
        db.close()
