from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.models import IdempotencyRecordModel, TaskSessionModel, WorkItemModel, WorkSessionModel, utc_now
from packages.core.uow import SqlAlchemyUnitOfWork


def test_session_audit_list_filters_and_detail_payload(
    authenticated_client, local_init_root
):
    client = authenticated_client
    repo = local_init_root / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "payments.py").write_text("Payment retry risk and rollback evidence.", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_session_audit",
            "name": "Session Audit",
            "slug": "session-audit",
            "git_remotes": ["git@example.com:session-audit.git"],
        },
    ).json()
    client.post(f"/projects/{project['id']}/initialize-local", json={"repo_path": str(repo)})

    analysis = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "介绍一下这个项目",
            "agent_type": "codex",
        },
    ).json()
    implementation = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "implement payment retry guard",
            "agent_type": "codex",
        },
    ).json()
    context = client.post(
        "/harness/plan-context",
        json={
            "session_id": implementation["session_id"],
            "query": "payment retry risk rollback",
            "token_budget": 1200,
        },
    ).json()
    skill = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "payment-risk-review",
            "name": "Payment Risk Review",
            "status": "approved",
            "definition": {
                "version": "1.0.0",
                "triggers": ["payment", "risk"],
                "input_schema": {"type": "object"},
                "instructions": "Review payment release risk.",
            },
        },
    ).json()
    skill_run = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={
            "session_id": implementation["session_id"],
            "input": {"change": "payment retry"},
            "context": {"summary": context["summary"]},
        },
    ).json()
    writeback = client.post(
        "/harness/prepare-writeback",
        json={
            "session_id": implementation["session_id"],
            "type": "development_update",
            "title": "Payment retry audit update",
            "content": "Implemented payment retry risk review and ran targeted checks.",
            "asset_refs": [],
        },
    ).json()
    client.post(
        "/harness/record-event",
        json={
            "session_id": implementation["session_id"],
            "event_type": "tests_run",
            "payload": {"command": "pytest tests/integration/api/test_sessions_api.py", "status": "passed"},
        },
    )

    filtered = client.get(f"/projects/{project['id']}/sessions?intent=implementation&q=payment").json()
    assert [session["id"] for session in filtered] == [implementation["session_id"]]
    assert filtered[0]["audit_counts"] == {
        "events": 2,
        "context_packs": 1,
        "skill_runs": 1,
        "writebacks": 1,
        "development_updates": 0,
    }

    closed_filter = client.get(f"/projects/{project['id']}/sessions?status=closed").json()
    assert closed_filter == []

    detail_response = client.get(f"/projects/{project['id']}/sessions/{implementation['session_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == implementation["session_id"]
    assert detail["work_item"]["id"] == implementation["work_item_id"]
    assert detail["work_item"]["title"] == "implement payment retry guard"
    assert detail["task_id"] is None
    assert detail["audit_counts"] == filtered[0]["audit_counts"]
    assert detail["context_packs"][0]["id"] == context["id"]
    assert detail["skill_runs"][0]["id"] == skill_run["id"]
    assert detail["skill_runs"][0]["skill_name"] == "Payment Risk Review"
    assert detail["writebacks"][0]["id"] == writeback["id"]
    assert detail["writebacks"][0]["title"] == "Payment retry audit update"
    assert [event["event_type"] for event in detail["events"]] == ["context_planned", "tests_run"]

    other_project = client.post(
        "/projects",
        json={
            "org_id": "org_session_audit",
            "name": "Other Session Audit",
            "slug": "other-session-audit",
            "git_remotes": ["git@example.com:other-session-audit.git"],
        },
    ).json()
    missing = client.get(f"/projects/{other_project['id']}/sessions/{implementation['session_id']}")
    assert missing.status_code == 404

    db = sessionmaker(bind=get_engine())()
    try:
        assert db.scalar(select(func.count()).select_from(TaskSessionModel)) == 0
        assert db.scalar(select(func.count()).select_from(WorkSessionModel)) == 2
    finally:
        db.close()


def test_legacy_sessions_backfilled_to_work_sessions_are_not_listed_twice():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_legacy_dupe",
            "name": "Legacy Dedupe",
            "slug": "legacy-dedupe",
            "git_remotes": [],
        },
    ).json()
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            work_item = WorkItemModel(
                org_id=project["org_id"],
                project_id=project["id"],
                external_key="LEG-1",
                title="Migrated legacy task",
                source="legacy",
            )
            db.add(work_item)
            db.flush()
            db.add(
                WorkSessionModel(
                    id="legacy-session-1",
                    work_item_id=work_item.id,
                    user_id="auth-bypass-user",
                    credential_id="auth-bypass-credential",
                    agent_type="codex",
                    intent="implementation",
                    legacy_imported=True,
                )
            )
            db.add(
                TaskSessionModel(
                    id="legacy-session-1",
                    org_id=project["org_id"],
                    project_id=project["id"],
                    task_id="LEG-1",
                    agent_type="codex",
                    intent="implementation",
                )
            )
            uow.commit()
    finally:
        db.close()

    sessions = client.get(f"/projects/{project['id']}/sessions").json()

    assert [session["id"] for session in sessions] == ["legacy-session-1"]
    assert sessions[0]["work_item"]["title"] == "Migrated legacy task"


def test_start_work_idempotency_replays_same_response_and_conflicts_on_payload_change():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_idempotency",
            "name": "Idempotency",
            "slug": "idempotency",
            "git_remotes": [],
        },
    ).json()
    payload = {
        "project_id": project["id"],
        "user_message": "帮我做 AG-128：实现支付状态流转",
        "agent_type": "codex",
    }

    first = client.post("/harness/start-work", headers={"Idempotency-Key": "same-key"}, json=payload)
    second = client.post("/harness/start-work", headers={"Idempotency-Key": "same-key"}, json=payload)
    conflict = client.post(
        "/harness/start-work",
        headers={"Idempotency-Key": "same-key"},
        json={**payload, "user_message": "帮我做 AG-128：实现其他内容"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"

    db = sessionmaker(bind=get_engine())()
    try:
        work_item = db.scalars(select(WorkItemModel).where(WorkItemModel.external_key == "AG-128")).one()
        assert db.scalar(select(func.count()).select_from(WorkSessionModel)) == 1
        assert db.scalar(select(func.count()).select_from(IdempotencyRecordModel)) == 1
        assert db.scalars(select(WorkSessionModel)).one().work_item_id == work_item.id
    finally:
        db.close()


def test_start_work_idempotency_conflicts_across_protocol_versions():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_idempotency_protocol",
            "name": "Idempotency Protocol",
            "slug": "idempotency-protocol",
            "git_remotes": [],
        },
    ).json()
    payload = {
        "project_id": project["id"],
        "user_message": "帮我做 AG-1510：协议幂等隔离",
        "agent_type": "codex",
    }

    legacy = client.post("/harness/start-work", headers={"Idempotency-Key": "protocol-key"}, json=payload)
    current = client.post(
        "/harness/start-work",
        headers={
            "Idempotency-Key": "protocol-key",
            "Agora-Protocol-Version": "1.1",
            "Agora-Connector-Version": "0.1.0",
        },
        json=payload,
    )

    assert legacy.status_code == 200
    assert current.status_code == 409
    detail = current.json()["detail"]
    assert detail["protocol_version"] == "1.1"
    assert detail["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_new_idempotency_key_creates_new_work_session_under_same_work_item():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_new_key",
            "name": "New Key",
            "slug": "new-key",
            "git_remotes": [],
        },
    ).json()
    payload = {
        "project_id": project["id"],
        "user_message": "帮我做 AG-128：实现支付状态流转",
        "agent_type": "codex",
    }

    first = client.post("/harness/start-work", headers={"Idempotency-Key": "first-key"}, json=payload).json()
    second = client.post("/harness/start-work", headers={"Idempotency-Key": "second-key"}, json=payload).json()

    assert first["session_id"] != second["session_id"]
    assert first["work_item_id"] == second["work_item_id"]

    db = sessionmaker(bind=get_engine())()
    try:
        assert db.scalar(select(func.count()).select_from(WorkItemModel)) == 1
        assert db.scalar(select(func.count()).select_from(WorkSessionModel)) == 2
    finally:
        db.close()


def test_expired_idempotency_key_is_tombstone_and_cannot_be_reused():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_expired_key",
            "name": "Expired Key",
            "slug": "expired-key",
            "git_remotes": [],
        },
    ).json()
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            db.add(
                IdempotencyRecordModel(
                    user_id="auth-bypass-user",
                    credential_id="auth-bypass-credential",
                    operation="harness.start_work",
                    idempotency_key="expired-key",
                    request_hash="old-request",
                    response_json={"session_id": "old-session"},
                    status="expired",
                    replay_expires_at=utc_now() - timedelta(seconds=1),
                )
            )
            uow.commit()
    finally:
        db.close()

    response = client.post(
        "/harness/start-work",
        headers={"Idempotency-Key": "expired-key"},
        json={
            "project_id": project["id"],
            "user_message": "实现过期幂等键保护",
            "agent_type": "codex",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_EXPIRED"

    db = sessionmaker(bind=get_engine())()
    try:
        assert db.scalar(select(func.count()).select_from(WorkSessionModel)) == 0
    finally:
        db.close()


def test_concurrent_start_work_with_same_key_creates_one_session_and_one_replay():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_concurrent_key",
            "name": "Concurrent Key",
            "slug": "concurrent-key",
            "git_remotes": [],
        },
    ).json()
    payload = {
        "project_id": project["id"],
        "user_message": "实现并发幂等创建",
        "agent_type": "codex",
    }

    def start_once():
        scoped_client = TestClient(app)
        return scoped_client.post(
            "/harness/start-work",
            headers={"Idempotency-Key": "concurrent-key"},
            json=payload,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: start_once(), range(2)))

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()

    db = sessionmaker(bind=get_engine())()
    try:
        assert db.scalar(select(func.count()).select_from(WorkSessionModel)) == 1
        assert db.scalar(select(func.count()).select_from(IdempotencyRecordModel)) == 1
    finally:
        db.close()
