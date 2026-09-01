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
    work_item = work_items[0]
    assert work_item["id"] == started["work_item_id"]
    assert work_item["project_id"] == project["id"]
    assert work_item["external_key"] == "AG-128"
    assert work_item["title"] == "实现支付状态流转"
    assert work_item["status"] == "active"
    assert work_item["stage"] == "analysis"
    assert work_item["source"] == "manual"
    assert work_item["session_count"] == 1
    assert work_item["participants"] == ["auth-bypass-user"]
    assert work_item["latest_context_state"] is None
    assert work_item["capability_pins"]["workflow_version_id"] == started["workflow_version_id"]
    assert work_item["workflow_execution"]["status"] == "running"
    assert [step["step_key"] for step in work_item["workflow_execution"]["steps"]] == [
        "analysis",
        "design",
        "review",
        "implementation",
        "self_test",
        "delivery",
    ]
    assert work_item["workflow_execution"]["steps"][0]["status"] == "running"
    assert work_item["workflow_execution"]["steps"][1]["status"] == "pending"


def test_work_item_detail_projects_sessions_and_latest_context_without_secrets(
    authenticated_client, local_init_root
):
    client = authenticated_client
    repo = local_init_root / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/refund.py").write_text("Refund retry idempotency implementation.", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_work_item_detail",
            "name": "Work Item Detail",
            "slug": "work-item-detail",
            "git_remotes": ["git@example.com:work-item-detail.git"],
        },
    ).json()
    client.post(f"/projects/{project['id']}/initialize-local", json={"repo_path": str(repo)})

    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-900：实现退款幂等",
            "agent_type": "codex",
        },
    ).json()
    context = client.post(
        "/harness/prepare-context",
        json={
            "session_id": started["session_id"],
            "query": "refund idempotency",
            "token_budget": 900,
        },
    ).json()
    client.post(
        "/harness/close-work",
        json={
            "session_id": started["session_id"],
            "status": "closed",
            "agent_summary": "完成 AG-900 退款幂等。",
            "test_result": "pytest tests/refund - passed",
        },
    )
    list_response = client.get(f"/projects/{project['id']}/work-items")

    response = client.get(f"/projects/{project['id']}/work-items/{started['work_item_id']}")

    assert list_response.status_code == 200
    listed_item = list_response.json()[0]
    assert len(listed_item["participants"]) == 1
    assert listed_item["participants"] != ["auth-bypass-user"]
    assert HUMAN_TOKEN not in str(listed_item["participants"])
    assert listed_item["latest_context_state"]["context_pack_id"] == context["context_pack_id"]
    assert listed_item["latest_context_state"]["provisional"] is True

    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == started["work_item_id"]
    assert detail["external_key"] == "AG-900"
    assert detail["title"] == "实现退款幂等"
    assert detail["participants"] == listed_item["participants"]
    assert detail["capability_pins"]["workflow_version_id"] == started["workflow_version_id"]
    assert detail["workflow_execution"]["status"] == "running"
    assert detail["workflow_execution"]["steps"][0]["step_key"] == "analysis"
    assert detail["latest_context_state"]["context_pack_id"] == context["context_pack_id"]
    assert detail["latest_context_state"]["provisional"] is True
    assert detail["latest_context_state"]["freshness"]["context_coverage"] != "fresh"
    assert detail["latest_context_state"]["budget"]["estimated_tokens"] <= 900
    assert detail["sessions"][0]["id"] == started["session_id"]
    assert detail["sessions"][0]["status"] == "closed"
    assert detail["sessions"][0]["work_item"]["id"] == started["work_item_id"]

    encoded = response.text
    assert "credential" not in encoded
    assert str(repo) not in encoded
    assert "repo_path" not in encoded


def test_work_item_detail_includes_workflow_artifacts_and_confirmations():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_work_item_workflow_audit",
            "name": "Work Item Workflow Audit",
            "slug": "work-item-workflow-audit",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-777：补充导出权限审计",
            "agent_type": "codex",
        },
    ).json()
    client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "完成导出权限审计分析。",
            "artifacts": [
                {
                    "type": "analysis_note",
                    "title": "AG-777 分析记录",
                    "content": "导出权限审计涉及角色、批量导出和操作日志。",
                    "metadata": {"path": "docs/tasks/AG-777/analysis.md"},
                }
            ],
            "human_confirmation": {
                "confirmation_type": "step_review",
                "decision": "approved",
                "comment": "分析范围确认。",
            },
        },
    )

    detail = client.get(f"/projects/{project['id']}/work-items/{started['work_item_id']}").json()

    analysis_step = detail["workflow_execution"]["steps"][0]
    assert analysis_step["step_key"] == "analysis"
    assert analysis_step["artifacts"][0]["title"] == "AG-777 分析记录"
    assert analysis_step["artifacts"][0]["metadata"] == {"path": "docs/tasks/AG-777/analysis.md"}
    assert analysis_step["human_confirmations"][0]["decision"] == "approved"
    assert analysis_step["human_confirmations"][0]["comment"] == "分析范围确认。"


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
