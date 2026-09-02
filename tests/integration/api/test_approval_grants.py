import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.api.main import app
from packages.core.models import CredentialModel, UserModel
from packages.core.passwords import hash_password
from packages.core.repositories.identities import IdentityRepository
from packages.core.services.approval_grants import APPROVAL_GRANT_TTL, approval_payload_digest
from packages.core.uow import SqlAlchemyUnitOfWork

HUMAN_TOKEN = "approval-human-token"
AGENT_TOKEN = "approval-agent-token"
CI_TOKEN = "approval-ci-token"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", CI_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def _session_client() -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        headers=_headers(HUMAN_TOKEN),
        json={
            "org_id": "local-org",
            "name": "Approval Matrix",
            "slug": "approval-matrix",
            "git_remotes": ["git@example.com:agora/approval-matrix.git"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _submit_proposal(client: TestClient, project_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/context/proposals",
        headers=_headers(AGENT_TOKEN),
        json={
            "type": "initial",
            "title": "初始上下文",
            "summary": "项目初始上下文。",
            "target_branch": "main",
            "content": {"overview": "审批矩阵验证项目。"},
            "source_anchors": [{"path": "docs/overview.md", "anchor": "L1"}],
            "provenance": {"tool": "codex", "agent_type": "codex"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _make_web_approver(client: TestClient, *, project_id: str, role: str = "owner") -> dict:
    db = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(db) as uow:
            user = UserModel(
                org_id="local-org",
                username="web-approver",
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

    login = client.post("/auth/login", json={"username": "web-approver", "password": "web-password"})
    assert login.status_code == 200, login.text
    csrf = login.json()["csrf_token"]
    reauth = client.post(
        "/auth/reauth",
        json={"password": "web-password"},
        headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:13140"},
    )
    assert reauth.status_code == 200, reauth.text
    return {"csrf_token": csrf}


def _approve_url(project_id: str, proposal_id: str) -> str:
    return f"/projects/{project_id}/context/proposals/{proposal_id}/approve"


def _proposal_digest(proposal_id: str, *, comment: str | None = None) -> str:
    """Compute the digest exactly as the approve endpoint does (ORM fields + full model_dump)."""
    from apps.api.routers.context_governance import RevisionSignal
    from packages.core.models import ContextProposalModel

    db = sessionmaker(bind=get_engine())()
    try:
        proposal = db.get(ContextProposalModel, proposal_id)
        assert proposal is not None
        return approval_payload_digest(
            proposal.id,
            proposal.content,
            proposal.source_anchors,
            RevisionSignal(target_branch="main", contains_to_commit=True).model_dump(),
            comment,
        )
    finally:
        db.close()


def _revision_signal() -> dict:
    return {"target_branch": "main", "contains_to_commit": True}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from apps.api.auth_session import rate_limiter

    rate_limiter.reset()
    yield


def test_agent_token_cannot_approve_context_proposal(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])

        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers=_headers(AGENT_TOKEN),
            json={"expected_head_revision_id": None, "comment": "agent 不能审批。", "revision_signal": _revision_signal()},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"


def test_ci_token_cannot_approve_context_proposal(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])

        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers=_headers(CI_TOKEN),
            json={"expected_head_revision_id": None, "comment": "CI 不能审批。", "revision_signal": _revision_signal()},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"


def test_personal_token_cannot_approve_context_proposal(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])

        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers=_headers(HUMAN_TOKEN),
            json={"expected_head_revision_id": None, "comment": "个人 token 不能审批。", "revision_signal": _revision_signal()},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"


def test_web_human_session_can_approve_without_grant(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])
        approver = _make_web_approver(client, project_id=project["id"])

        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={"expected_head_revision_id": None, "comment": "Web 会话审批。", "revision_signal": _revision_signal()},
        )

        assert response.status_code == 200, response.text


def test_approval_grant_is_single_use_and_bound(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])
        approver = _make_web_approver(client, project_id=project["id"])

        digest = _proposal_digest(proposal["id"], comment="带 grant 审批。")
        grant = client.post(
            "/approval-grants",
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "object_type": "context_proposal",
                "object_id": proposal["id"],
                "payload_digest": digest,
                "decision": "approved",
            },
        )
        assert grant.status_code == 201, grant.text
        grant_id = grant.json()["grant_id"]

        approve = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "expected_head_revision_id": None,
                "comment": "带 grant 审批。",
                "revision_signal": _revision_signal(),
                "approval_grant_id": grant_id,
            },
        )
        assert approve.status_code == 200, approve.text

        # replaying the same grant on the same object must be rejected as used
        reused = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "expected_head_revision_id": None,
                "comment": "带 grant 审批。",
                "revision_signal": _revision_signal(),
                "approval_grant_id": grant_id,
            },
        )
        assert reused.status_code == 403
        assert reused.json()["detail"]["code"] == "APPROVAL_GRANT_USED"


def test_approval_grant_digest_mismatch_rejected(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])
        approver = _make_web_approver(client, project_id=project["id"])

        wrong_digest = approval_payload_digest("tampered")
        grant = client.post(
            "/approval-grants",
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "object_type": "context_proposal",
                "object_id": proposal["id"],
                "payload_digest": wrong_digest,
                "decision": "approved",
            },
        ).json()

        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "expected_head_revision_id": None,
                "comment": "digest 不匹配。",
                "revision_signal": _revision_signal(),
                "approval_grant_id": grant["grant_id"],
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "APPROVAL_GRANT_DIGEST_MISMATCH"


def test_approval_grant_expired_rejected(monkeypatch):
    import packages.core.services.approval_grants as approval_service

    original_ttl = approval_service.APPROVAL_GRANT_TTL
    approval_service.APPROVAL_GRANT_TTL = APPROVAL_GRANT_TTL  # keep import used
    from datetime import timedelta

    monkeypatch.setattr(approval_service, "APPROVAL_GRANT_TTL", timedelta(milliseconds=1))

    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        proposal = _submit_proposal(client, project["id"])
        approver = _make_web_approver(client, project_id=project["id"])

        digest = _proposal_digest(proposal["id"], comment="过期 grant。")
        grant = client.post(
            "/approval-grants",
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "object_type": "context_proposal",
                "object_id": proposal["id"],
                "payload_digest": digest,
                "decision": "approved",
            },
        ).json()

        import time

        time.sleep(0.01)
        response = client.post(
            _approve_url(project["id"], proposal["id"]),
            headers={"X-CSRF-Token": approver["csrf_token"], "Origin": "http://127.0.0.1:13140"},
            json={
                "expected_head_revision_id": None,
                "comment": "过期 grant。",
                "revision_signal": _revision_signal(),
                "approval_grant_id": grant["grant_id"],
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "APPROVAL_GRANT_EXPIRED"
        monkeypatch.setattr(approval_service, "APPROVAL_GRANT_TTL", original_ttl)


def test_issue_grant_requires_reauthentication(monkeypatch):
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        db = sessionmaker(bind=get_engine())()
        try:
            with SqlAlchemyUnitOfWork(db) as uow:
                user = UserModel(
                    org_id="local-org",
                    username="no-reauth",
                    display_name="No Reauth",
                    status="active",
                    is_placeholder=False,
                    password_hash=hash_password("no-reauth-password"),
                )
                db.add(user)
                db.flush()
                IdentityRepository(db).grant_membership(project_id=project["id"], user_id=user.id, role="owner")
                uow.commit()
        finally:
            db.close()

        login = client.post("/auth/login", json={"username": "no-reauth", "password": "no-reauth-password"})
        csrf = login.json()["csrf_token"]

        grant = client.post(
            "/approval-grants",
            headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:13140"},
            json={"object_type": "context_proposal", "object_id": "x", "payload_digest": "d", "decision": "approved"},
        )

        assert grant.status_code == 403
        assert grant.json()["detail"]["code"] == "REAUTH_REQUIRED"


def test_agent_can_complete_workflow_step_but_not_approve(monkeypatch):
    # Low-risk workflow acknowledgment via Agent token stays allowed and is
    # distinct from Approval (which the same agent cannot perform).
    _production_auth(monkeypatch)
    with _session_client() as client:
        project = _create_project(client)
        started = client.post(
            "/harness/start-work",
            headers=_headers(AGENT_TOKEN),
            json={"project_id": project["id"], "user_message": "低风险工作流确认", "agent_type": "codex"},
        ).json()
        completed = client.post(
            "/harness/complete-workflow-step",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "agent-ack-key",
            },
            json={"session_id": started["session_id"], "step_key": "analysis", "summary": "代理摘要完成。"},
        )
        assert completed.status_code == 200

        # same agent can submit a skill candidate but cannot approve it
        submitted = client.post(
            "/harness/submit-skill-candidate",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "agent-skill-key",
            },
            json={
                "session_id": started["session_id"],
                "slug": "release-review",
                "name": "Release Review",
                "summary": "初稿。",
                "triggers": ["release"],
                "instructions": "初稿。",
            },
        )
        assert submitted.status_code == 201, submitted.text
        skill_id = submitted.json()["skill"]["id"]
        denied = client.post(
            f"/projects/{project['id']}/skills/{skill_id}/approve",
            headers=_headers(AGENT_TOKEN),
        )
        assert denied.status_code == 403
        assert denied.json()["detail"]["code"] == "APPROVAL_CREDENTIAL_REQUIRED"
