"""PR3 B2: API token lifecycle (issue/list/rotate) tests."""

from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.auth import hash_token


ORG = "credentials-org"


def _client() -> TestClient:
    return TestClient(app)


def _create_active_user(client: TestClient, username: str) -> dict:
    created = client.post(
        "/users",
        json={"org_id": ORG, "username": username, "display_name": username.title()},
    ).json()
    activated = client.post(
        "/users/activate",
        json={
            "activation_token": created["activation_token"],
            "new_password": f"{username}-password-1",
        },
    )
    assert activated.status_code == 200
    return activated.json()["user"]


def test_issue_lists_and_rotates_api_credentials():
    client = _client()
    user = _create_active_user(client, "alice")

    issued = client.post(
        f"/users/{user['id']}/credentials",
        json={"kind": "agent", "label": "CI runner"},
    )
    assert issued.status_code == 201
    body = issued.json()
    token = body["token"]
    assert len(token) >= 32
    assert body["credential"]["kind"] == "agent"
    assert body["credential"]["label"] == "CI runner"
    assert body["credential"]["status"] == "active"
    assert body["credential"]["expires_at"] is None

    listed = client.get(f"/users/{user['id']}/credentials").json()
    assert len(listed) == 1
    serialized = str(listed)
    assert token not in serialized  # plaintext is never returned on list

    rotated = client.post(
        f"/users/{user['id']}/credentials/{body['credential']['id']}/rotate"
    )
    assert rotated.status_code == 200
    new_token = rotated.json()["token"]
    assert new_token != token
    assert rotated.json()["credential"]["kind"] == "agent"
    assert rotated.json()["credential"]["label"] == "CI runner"

    after = client.get(f"/users/{user['id']}/credentials").json()
    statuses = {cred["id"]: cred["status"] for cred in after}
    assert statuses[body["credential"]["id"]] == "revoked"
    assert len(after) == 2

    # Plaintext round-trip through the stored hash (old invalid, new valid).
    from apps.api.dependencies import get_engine
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=get_engine())()
    try:
        from packages.core.repositories.identities import IdentityRepository

        repo = IdentityRepository(session)
        assert repo.get_credential_by_hash(hash_token(token)) is None
        fresh = repo.get_credential_by_hash(hash_token(new_token))
        assert fresh is not None and fresh.kind == "agent" and fresh.label == "CI runner"
    finally:
        session.close()


def test_issue_supports_human_kind_with_expiry():
    client = _client()
    user = _create_active_user(client, "bob")
    issued = client.post(
        f"/users/{user['id']}/credentials",
        json={
            "kind": "human",
            "label": "bob laptop",
            "expires_at": "2030-01-01T00:00:00Z",
        },
    )
    assert issued.status_code == 201
    assert issued.json()["credential"]["kind"] == "human"
    assert issued.json()["credential"]["expires_at"].startswith("2030-01-01")


def test_issue_validates_input():
    client = _client()
    user = _create_active_user(client, "carol")

    bad_kind = client.post(
        f"/users/{user['id']}/credentials",
        json={"kind": "superuser"},
    )
    assert bad_kind.status_code == 403
    assert bad_kind.json()["detail"]["code"] == "KIND_NOT_ALLOWED"

    past = client.post(
        f"/users/{user['id']}/credentials",
        json={"kind": "agent", "expires_at": "2020-01-01T00:00:00Z"},
    )
    assert past.status_code == 400
    assert past.json()["detail"]["code"] == "EXPIRY_IN_PAST"

    malformed = client.post(
        f"/users/{user['id']}/credentials",
        json={"kind": "agent", "expires_at": "not-a-date"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["detail"]["code"] == "EXPIRY_INVALID"

    missing_user = client.post(
        "/users/does-not-exist/credentials",
        json={"kind": "agent"},
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_rotate_rejects_single_use_and_unknown_credentials():
    client = _client()
    user = _create_active_user(client, "dave")

    unknown = client.post(
        f"/users/{user['id']}/credentials/nope/rotate",
    )
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "CREDENTIAL_NOT_FOUND"

    created = client.post(
        "/users",
        json={"org_id": ORG, "username": "erin", "display_name": "Erin"},
    ).json()
    user2 = created["user"]
    activation = client.post(
        f"/users/{user2['id']}/credentials",
        json={"kind": "agent", "label": "rot"},
    )
    assert activation.status_code == 201
    rotated_twice = client.post(
        f"/users/{user2['id']}/credentials/{activation.json()['credential']['id']}/rotate"
    )
    assert rotated_twice.status_code == 200
    # rotating a rotated credential (now revoked) is rejected.
    third = client.post(
        f"/users/{user2['id']}/credentials/{activation.json()['credential']['id']}/rotate"
    )
    assert third.status_code == 400
    assert third.json()["detail"]["code"] == "CREDENTIAL_NOT_ACTIVE"


def test_credential_actions_are_audited():
    client = _client()
    user = _create_active_user(client, "frank")

    issued = client.post(
        f"/users/{user['id']}/credentials",
        json={"kind": "ci", "label": "audit me"},
    )
    assert issued.status_code == 201
    client.post(
        f"/users/{user['id']}/credentials/{issued.json()['credential']['id']}/rotate"
    )

    from apps.api.dependencies import get_engine
    from sqlalchemy.orm import sessionmaker

    from packages.core.repositories.security import SecurityRepository

    session = sessionmaker(bind=get_engine())()
    try:
        actions = {e.action for e in SecurityRepository(session).list_by_org(ORG)}
        assert {"credential.issue", "credential.rotate"} <= actions
    finally:
        session.close()
