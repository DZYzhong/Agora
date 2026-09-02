from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.repositories.security import SecurityRepository
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine


def _client():
    return TestClient(app)


def test_admin_creates_user_and_returns_one_time_activation_token():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "org_api", "username": "alice", "display_name": "Alice"},
    )

    assert created.status_code == 201
    body = created.json()
    assert body["activation_token"]
    assert body["user"]["status"] == "pending_activation"
    assert body["user"]["username"] == "alice"
    assert "deliver" in body["delivery"]


def test_activation_token_is_single_use():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "org_api", "username": "bob", "display_name": "Bob"},
    ).json()

    first = client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": "bob-password-1"},
    )
    assert first.status_code == 200
    assert first.json()["user"]["status"] == "active"

    second = client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": "bob-password-2"},
    )
    assert second.status_code == 400
    assert second.json()["detail"]["code"] == "ACTIVATION_TOKEN_INVALID"


def test_activate_rejects_bogus_token():
    client = _client()
    response = client.post(
        "/users/activate",
        json={"activation_token": "not-a-real-token", "new_password": "password-1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ACTIVATION_TOKEN_INVALID"


def test_reset_flow_issue_and_consume():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "org_api", "username": "carol", "display_name": "Carol"},
    ).json()
    client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": "original-password"},
    )

    reset = client.post(f"/users/{created['user']['id']}/reset")
    assert reset.status_code == 200
    reset_body = reset.json()
    assert reset_body["reset_token"]
    assert reset_body["user_id"] == created["user"]["id"]

    used = client.post(
        "/users/reset-password",
        json={"reset_token": reset_body["reset_token"], "new_password": "rotated-password"},
    )
    assert used.status_code == 200
    assert used.json()["user"]["status"] == "active"

    reused = client.post(
        "/users/reset-password",
        json={"reset_token": reset_body["reset_token"], "new_password": "again-password"},
    )
    assert reused.status_code == 400
    assert reused.json()["detail"]["code"] == "RESET_TOKEN_INVALID"


def test_disable_user_revokes_credentials():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "org_api", "username": "dave", "display_name": "Dave"},
    ).json()

    disabled = client.post(f"/users/{created['user']['id']}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["user"]["status"] == "disabled"

    activate_attempt = client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": "dave-password"},
    )
    assert activate_attempt.status_code == 400

    enabled = client.post(f"/users/{created['user']['id']}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["user"]["status"] == "active"


def test_list_users_shows_managed_users():
    client = _client()
    client.post("/users", json={"org_id": "org_api", "username": "erin", "display_name": "Erin"})

    listing = client.get("/users?org_id=org_api")

    assert listing.status_code == 200
    usernames = {user["username"] for user in listing.json()["users"]}
    assert "erin" in usernames


def test_create_user_requires_org_id_for_bypass():
    client = _client()
    response = client.post("/users", json={"username": "noorg", "display_name": "No Org"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ORG_ID_REQUIRED"


def test_identity_api_actions_are_audited():
    client = _client()
    created = client.post(
        "/users",
        json={"org_id": "org_audit", "username": "frank", "display_name": "Frank"},
    ).json()
    client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": "frank-password"},
    )

    session = sessionmaker(bind=get_engine())()
    try:
        actions = {event.action for event in SecurityRepository(session).list_by_org("org_audit")}
    finally:
        session.close()
    assert {"user.create", "user.activate"} <= actions
