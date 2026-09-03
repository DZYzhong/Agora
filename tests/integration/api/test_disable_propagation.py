"""PR3 B3: disable propagation — credentials, web sessions and approval
grants all become unusable when a user is disabled."""

from datetime import timedelta

from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.models import utc_now
from packages.core.repositories.approval_grants import ApprovalGrantRepository
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.security import SecurityRepository
from packages.core.repositories.sessions_auth import WebSessionRepository


def _client() -> TestClient:
    return TestClient(app)


def test_disable_revokes_credentials_sessions_and_approval_grants():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "disable-org", "username": "grace", "display_name": "Grace"},
    ).json()
    user_id = created["user"]["id"]

    # Issue an agent credential through the API.
    issued = client.post(
        f"/users/{user_id}/credentials",
        json={"kind": "agent", "label": "propagation-runner"},
    )
    assert issued.status_code == 201
    credential_id = issued.json()["credential"]["id"]

    from apps.api.dependencies import get_engine
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    session = sessionmaker(bind=engine)()
    now = utc_now()
    try:
        with session.begin():
            # Seed an active approval grant and a web session for the user.
            grant = ApprovalGrantRepository(session).create(
                org_id="disable-org",
                user_id=user_id,
                session_id=None,
                object_type="context_proposal",
                object_id="proposal-1",
                payload_digest="digest",
                decision="approve",
                policy_version="1",
                expires_at=now + timedelta(hours=1),
                now=now,
            )
            grant_id = grant.id
            WebSessionRepository(session).create(
                user_id=user_id,
                org_id="disable-org",
                token_hash="disable-session-hash",
                csrf_secret_hash="disable-csrf-hash",
                expires_at=now + timedelta(hours=12),
                idle_expires_at=now + timedelta(minutes=30),
                now=now,
            )
    finally:
        session.close()

    disabled = client.post(f"/users/{user_id}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["user"]["status"] == "disabled"

    session = sessionmaker(bind=engine)()
    try:
        repo = IdentityRepository(session)
        credential = repo.get_credential(credential_id)
        assert credential.status == "revoked"

        grant_record = ApprovalGrantRepository(session).get(grant_id)
        assert grant_record.consumed_at is not None

        web = WebSessionRepository(session)
        active_session = web.get_active_by_token_hash(
            "disable-session-hash", now=utc_now()
        )
        assert active_session is None

        audit = SecurityRepository(session).list_by_org("disable-org")
        disable_events = [e for e in audit if e.action == "user.disable"]
        assert disable_events
        reason = disable_events[-1].reason or ""
        assert reason == "2 credentials, 1 sessions, 1 approval grants revoked"
    finally:
        session.close()
