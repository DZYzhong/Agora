from fastapi.testclient import TestClient
from uuid import uuid4

from packages.core.passwords import hash_password
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.auth import hash_token, token_diagnostic_prefix
from packages.core.models import CredentialModel, SecurityAuditEventModel, UserModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.uow import SqlAlchemyUnitOfWork

HUMAN_TOKEN = "context-human-token"
AGENT_TOKEN = "context-agent-token"
MEMBER_TOKEN = "context-member-token"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _session_client() -> TestClient:
    # Secure cookies are only sent by httpx over https.
    return TestClient(app, base_url="https://testserver")


def _csrf_headers(csrf_token: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf_token, "Origin": "http://127.0.0.1:13140"}


def _web_approver(client: TestClient, *, project_id: str, role: str = "owner") -> str:
    """Create a Web human user with the given project role, log in and reauthenticate.

    Returns the CSRF token of the logged-in session.
    """
    from packages.core.models import UserModel

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
    reauth = client.post(
        "/auth/reauth",
        json={"password": "web-password"},
        headers=_csrf_headers(csrf),
    )
    assert reauth.status_code == 200, reauth.text
    return csrf


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        headers=_headers(HUMAN_TOKEN),
        json={
            "org_id": "ignored-org",
            "name": "Context Governance",
            "slug": "context-governance",
            "git_remotes": ["git@example.com:agora/context-governance.git"],
            "default_branch": "main",
        },
    )
    assert response.status_code == 201
    return response.json()


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


def _proposal_payload(expected_head_revision_id: str | None = None) -> dict:
    return {
        "type": "initial",
        "title": "Initial project context",
        "summary": "支付服务上下文初始版本。",
        "target_branch": "main",
        "expected_head_revision_id": expected_head_revision_id,
        "to_commit_sha": "abc123",
        "content": {
            "project_overview": "支付服务负责状态流转和审计。",
            "domains": ["payments"],
            "modules": [{"path": "src/payments/state_machine.py", "summary": "支付状态机"}],
            "risks": ["重复请求可能产生重复审计事件"],
            "test_strategy": ["状态流转单元测试"],
        },
        "source_anchors": [
            {
                "kind": "code",
                "path": "src/payments/state_machine.py",
                "start_line": 1,
                "end_line": 12,
            }
        ],
        "provenance": {
            "generating_tool": "codex",
            "schema_version": "context-revision/v1",
            "repository_commit": "abc123",
        },
    }


def test_agent_submits_context_proposal_and_human_accepts_revision(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])

        create_response = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        )
        assert create_response.status_code == 201
        proposal = create_response.json()
        assert proposal["status"] == "submitted"
        assert proposal["stream"]["branch"] == "main"
        assert proposal["stream"]["head_revision_id"] is None
        assert proposal["source_anchors"][0]["path"] == "src/payments/state_machine.py"

        approve_response = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "comment": "同意作为项目初始上下文。",
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        )
        assert approve_response.status_code == 200
        accepted = approve_response.json()
        assert accepted["proposal"]["status"] == "approved"
        assert accepted["revision"]["id"] == accepted["stream"]["head_revision_id"]
        assert accepted["revision"]["content"]["project_overview"] == "支付服务负责状态流转和审计。"
        assert accepted["revision"]["source_anchors"][0]["path"] == "src/payments/state_machine.py"
        assert accepted["outbox_event"]["type"] == "context_head_changed"

        streams = client.get(f"/projects/{project['id']}/context/streams", headers=_headers(HUMAN_TOKEN)).json()
        assert streams[0]["head_revision_id"] == accepted["revision"]["id"]


def test_context_approval_rejects_agent_and_non_reviewer_member_with_audit(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        _grant_member(project["id"], role="member")

        payload = {
            "expected_head_revision_id": None,
            "comment": "尝试审批。",
            "revision_signal": {
                "target_branch": "main",
                "observed_head_sha": "abc123",
                "contains_to_commit": True,
            },
        }
        agent_denied = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_headers(AGENT_TOKEN),
            json=payload,
        )
        # a member role cannot approve even with a reauthenticated Web session
        member_approver = _web_approver(client, project_id=project["id"], role="member")
        member_denied = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_csrf_headers(member_approver),
            json=payload,
        )

    assert agent_denied.status_code == 403
    assert agent_denied.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"
    assert member_denied.status_code == 403
    assert member_denied.json()["detail"]["code"] == "PROJECT_ROLE_REQUIRED"

    with sessionmaker(bind=get_engine())() as db:
        events = db.query(SecurityAuditEventModel).filter_by(project_id=project["id"]).order_by(SecurityAuditEventModel.created_at).all()
        assert [event.action for event in events] == ["context_proposal.approve", "context_proposal.approve"]
        assert [event.decision for event in events] == ["deny", "deny"]
        assert {event.reason for event in events} == {"APPROVAL_CREDENTIAL_REQUIRED", "PROJECT_ROLE_REQUIRED"}


def test_accepting_stale_context_proposal_marks_needs_rebase(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])
        first = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{first['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        ).json()

        stale = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(expected_head_revision_id=None),
        ).json()
        stale_accept = client.post(
            f"/projects/{project['id']}/context/proposals/{stale['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        )

        assert stale_accept.status_code == 409
        body = stale_accept.json()
        assert body["proposal"]["status"] == "needs_rebase"
        assert body["stream"]["head_revision_id"] == accepted["revision"]["id"]


def test_multiple_same_head_context_proposals_cannot_overwrite_stream_head(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])
        proposals = [
            client.post(
                f"/projects/{project['id']}/context/proposals",
                headers=_headers(AGENT_TOKEN),
                json={
                    **_proposal_payload(expected_head_revision_id=None),
                    "title": f"Concurrent context proposal {index}",
                    "to_commit_sha": f"candidate-{index}",
                },
            ).json()
            for index in range(3)
        ]

        results = [
            client.post(
                f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
                headers=_csrf_headers(approver),
                json={
                    "expected_head_revision_id": None,
                    "revision_signal": {
                        "target_branch": "main",
                        "observed_head_sha": proposal["to_commit_sha"],
                        "contains_to_commit": True,
                    },
                },
            )
            for proposal in proposals
        ]

        approved = [response for response in results if response.status_code == 200]
        rebased = [response for response in results if response.status_code == 409]
        streams = client.get(f"/projects/{project['id']}/context/streams", headers=_headers(HUMAN_TOKEN)).json()

    assert len(approved) == 1
    assert len(rebased) == 2
    assert {response.json()["proposal"]["status"] for response in rebased} == {"needs_rebase"}
    assert streams[0]["head_revision_id"] == approved[0].json()["revision"]["id"]


def test_prepare_context_uses_accepted_revision_after_approval(
    monkeypatch, local_init_root
):
    _production_auth(monkeypatch)
    repo = local_init_root / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/payments.py").write_text("payment state machine", encoding="utf-8")
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])
        client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_headers(HUMAN_TOKEN),
            json={"repo_path": str(repo)},
        )
        proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        ).json()
        started = client.post(
            "/harness/start-work",
            headers=_headers(AGENT_TOKEN),
            json={
                "project_id": project["id"],
                "user_message": "帮我做 PAY-242：补充退款状态审计",
                "agent_type": "codex",
            },
        ).json()

        bundle = client.post(
            "/harness/prepare-context",
            headers=_headers(AGENT_TOKEN),
            json={
                "session_id": started["session_id"],
                "query": "退款状态审计",
                "token_budget": 1400,
            },
        ).json()

        assert bundle["provisional"] is False
        assert bundle["freshness"]["context_coverage"] == "fresh"
        assert bundle["freshness"]["accepted_revision_id"] == accepted["revision"]["id"]
        assert bundle["capability_pins"]["context_revision_id"] == accepted["revision"]["id"]


def test_ai_tool_submits_context_proposal_through_harness_session(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        started = client.post(
            "/harness/start-work",
            headers=_headers(AGENT_TOKEN),
            json={
                "project_id": project["id"],
                "user_message": "帮我做 PAY-318：退款状态变更增加审计记录",
                "agent_type": "codex",
                "branch_name": "feature/PAY-318-refund-audit",
            },
        ).json()

        response = client.post(
            "/harness/submit-context-proposal",
            headers=_headers(AGENT_TOKEN),
            json={
                **_proposal_payload(),
                "session_id": started["session_id"],
                "type": "task_update",
                "title": "PAY-318 退款审计上下文更新",
                "summary": "记录退款状态审计的模块边界、风险和测试策略。",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["protocol_version"] == "1.0"
        assert body["operation"] == "submit_context_proposal"
        assert body["proposal"]["status"] == "submitted"
        assert body["proposal"]["project_id"] == project["id"]
        assert body["proposal"]["session_id"] == started["session_id"]
        assert body["proposal"]["work_item_id"] == started["work_item_id"]
        assert body["stream"]["branch"] == "main"
        assert body["capability_pins"]["context_revision_id"] is None
        assert body["next_actions"][0]["type"] == "human_review_context_proposal"


def test_feature_branch_context_proposal_updates_feature_stream_without_overwriting_main(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])
        main_proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        main_accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{main_proposal['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        ).json()
        feature_payload = {
            **_proposal_payload(expected_head_revision_id=None),
            "type": "task_update",
            "title": "PAY-318 feature branch context",
            "target_branch": "feature/PAY-318-refund-audit",
            "to_commit_sha": "feature123",
            "provenance": {
                "generating_tool": "codex",
                "schema_version": "context-revision/v1",
                "repository_commit": "feature123",
                "source_branch": "feature/PAY-318-refund-audit",
            },
        }
        feature_proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=feature_payload,
        ).json()

        feature_accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{feature_proposal['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "feature/PAY-318-refund-audit",
                    "observed_head_sha": "feature123",
                    "contains_to_commit": True,
                },
            },
        ).json()

        streams = client.get(f"/projects/{project['id']}/context/streams", headers=_headers(HUMAN_TOKEN)).json()
        stream_heads = {stream["branch"]: stream["head_revision_id"] for stream in streams}
        assert feature_accepted["stream"]["branch"] == "feature/PAY-318-refund-audit"
        assert stream_heads["main"] == main_accepted["revision"]["id"]
        assert stream_heads["feature/PAY-318-refund-audit"] == feature_accepted["revision"]["id"]


def test_feature_branch_context_cannot_update_default_stream_without_merge_signal(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        approver = _web_approver(client, project_id=project["id"])
        proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json={
                **_proposal_payload(),
                "type": "task_update",
                "title": "PAY-319 merge candidate",
                "target_branch": "main",
                "to_commit_sha": "feature456",
                "provenance": {
                    "generating_tool": "codex",
                    "schema_version": "context-revision/v1",
                    "repository_commit": "feature456",
                    "source_branch": "feature/PAY-319-refund-ledger",
                },
            },
        ).json()

        response = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_csrf_headers(approver),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "feature456",
                    "contains_to_commit": True,
                    "merge_target_branch": "main",
                    "merged_to_target": False,
                },
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Feature branch context cannot update the default stream before merge reachability is proven"


def test_stream_revisions_endpoint_lists_history_and_marks_head(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        initial = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        approver = _web_approver(client, project_id=project["id"])
        for comment in ("first", "second"):
            resp = client.post(
                f"/projects/{project['id']}/context/proposals/{initial['id']}/approve",
                headers=_csrf_headers(approver),
                json={
                    "expected_head_revision_id": None,
                    "comment": comment,
                    "revision_signal": {
                        "target_branch": "main",
                        "observed_head_sha": "abc123",
                        "contains_to_commit": True,
                    },
                },
            )
            assert resp.status_code in (200, 409)

        streams = client.get(f"/projects/{project['id']}/context/streams", headers=_headers(HUMAN_TOKEN)).json()
        assert streams, "no stream created"
        stream = streams[0]

        result = client.get(
            f"/projects/{project['id']}/context/streams/{stream['id']}/revisions",
            headers=_headers(HUMAN_TOKEN),
        )
        assert result.status_code == 200
        body = result.json()
        assert body["stream"]["id"] == stream["id"]
        assert "revisions" in body
        for revision in body["revisions"]:
            assert "is_head" in revision
        head_marks = [revision for revision in body["revisions"] if revision["is_head"]]
        assert len(head_marks) == 1
        assert head_marks[0]["id"] == stream["head_revision_id"]


def test_stream_revisions_endpoint_rejects_unknown_stream(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        project = _create_project(client)
        response = client.get(
            f"/projects/{project['id']}/context/streams/nope/revisions",
            headers=_headers(HUMAN_TOKEN),
        )
        assert response.status_code == 404
