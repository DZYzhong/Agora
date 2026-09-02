from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.auth_session import rate_limiter


def _session_client() -> TestClient:
    # Secure cookies are only sent by httpx over https; the Web app runs on a
    # localhost origin which browsers treat as a secure context.
    return TestClient(app, base_url="https://testserver")


def _make_activated_user(client: TestClient, *, org_id: str, username: str, password: str) -> dict:
    created = client.post(
        "/users",
        json={"org_id": org_id, "username": username, "display_name": username.title()},
    ).json()
    client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": password},
    )
    return created["user"]


def test_login_sets_secure_http_only_samesite_cookie_and_returns_csrf_token():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="alice", password="alice-password")

    response = client.post("/auth/login", json={"username": "alice", "password": "alice-password"})

    assert response.status_code == 200
    body = response.json()
    assert body["csrf_token"]
    assert body["user"]["username"] == "alice"
    set_cookie = response.headers.get("set-cookie", "")
    assert "agora_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Secure" in set_cookie
    # the raw session token (the cookie value) must never appear in the response body
    import re
    match = re.search(r"agora_session=([^;]+)", set_cookie)
    assert match
    assert match.group(1) not in response.text


def test_login_rejects_wrong_password():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="bob", password="bob-password")

    response = client.post("/auth/login", json={"username": "bob", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_rate_limited_per_username():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="carol", password="carol-password")

    for _ in range(5):
        response = client.post("/auth/login", json={"username": "carol", "password": "wrong"})
        assert response.status_code == 401

    response = client.post("/auth/login", json={"username": "carol", "password": "carol-password"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "LOGIN_RATE_LIMITED"


def test_current_session_returns_user_and_csrf_token():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="dave", password="dave-password")
    client.post("/auth/login", json={"username": "dave", "password": "dave-password"})

    response = client.get("/auth/session")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "dave"
    assert body["csrf_token"]


def test_current_session_without_cookie_is_unauthorized():
    client = TestClient(app)
    response = client.get("/auth/session")
    assert response.status_code == 401


def test_state_change_requires_csrf_token_and_origin():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="erin", password="erin-password")
    login = client.post("/auth/login", json={"username": "erin", "password": "erin-password"}).json()
    csrf_token = login["csrf_token"]

    # no CSRF token (but valid Origin) -> token check rejects
    no_token = client.post(
        "/auth/reauth",
        json={"password": "erin-password"},
        headers={"Origin": "http://127.0.0.1:13140"},
    )
    assert no_token.status_code == 403
    assert no_token.json()["detail"]["code"] == "CSRF_TOKEN_REQUIRED"

    # wrong CSRF token
    wrong_token = client.post(
        "/auth/reauth",
        json={"password": "erin-password"},
        headers={"X-CSRF-Token": "not-the-token", "Origin": "http://127.0.0.1:13140"},
    )
    assert wrong_token.status_code == 403

    # correct token but disallowed origin
    bad_origin = client.post(
        "/auth/reauth",
        json={"password": "erin-password"},
        headers={"X-CSRF-Token": csrf_token, "Origin": "https://evil.example.com"},
    )
    assert bad_origin.status_code == 403
    assert bad_origin.json()["detail"]["code"] == "CSRF_ORIGIN_REJECTED"

    # correct token + allowed origin succeeds
    ok = client.post(
        "/auth/reauth",
        json={"password": "erin-password"},
        headers={"X-CSRF-Token": csrf_token, "Origin": "http://127.0.0.1:13140"},
    )
    assert ok.status_code == 200
    assert ok.json()["reauthenticated"] is True


def test_reauth_rejects_wrong_password():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="frank", password="frank-password")
    login = client.post("/auth/login", json={"username": "frank", "password": "frank-password"}).json()

    response = client.post(
        "/auth/reauth",
        json={"password": "wrong-password"},
        headers={"X-CSRF-Token": login["csrf_token"], "Origin": "http://127.0.0.1:13140"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_logout_revokes_session():
    client = _session_client()
    _make_activated_user(client, org_id="org_session", username="grace", password="grace-password")
    login = client.post("/auth/login", json={"username": "grace", "password": "grace-password"}).json()

    logout = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": login["csrf_token"], "Origin": "http://127.0.0.1:13140"},
    )
    assert logout.status_code == 200

    current = client.get("/auth/session")
    assert current.status_code == 401


def test_disabled_user_session_is_revoked():
    client = TestClient(app)
    user = _make_activated_user(client, org_id="org_session", username="heidi", password="heidi-password")
    client.post("/auth/login", json={"username": "heidi", "password": "heidi-password"})

    client.post(f"/users/{user['id']}/disable")

    current = client.get("/auth/session")
    assert current.status_code == 401


def test_bearer_mutations_are_not_subject_to_csrf():
    # Agent/CI bearer flows are not browser-cookie flows; the CSRF middleware
    # must not block them even though they are state-changing.
    client = TestClient(app)
    response = client.post(
        "/projects",
        json={"org_id": "org_no_csrf", "name": "NoCsrf", "slug": "no-csrf", "git_remotes": []},
    )
    assert response.status_code == 201
