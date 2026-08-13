from fastapi.testclient import TestClient

from apps.api.main import app


def test_session_audit_list_filters_and_detail_payload(tmp_path):
    client = TestClient(app)
    repo = tmp_path / "repo"
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
    }

    closed_filter = client.get(f"/projects/{project['id']}/sessions?status=closed").json()
    assert closed_filter == []

    detail_response = client.get(f"/projects/{project['id']}/sessions/{implementation['session_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == implementation["session_id"]
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
