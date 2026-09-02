import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.middleware import stable_error_response
from packages.core.upload_policy import MAX_JSON_BODY_BYTES


def test_oversized_json_body_rejected_with_stable_error():
    client = TestClient(app)
    oversized = {"data": "x" * (MAX_JSON_BODY_BYTES + 1000)}
    response = client.post("/projects", json=oversized)
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "PAYLOAD_TOO_LARGE"


def test_normal_body_accepted():
    client = TestClient(app)
    response = client.post(
        "/projects",
        json={"org_id": "org_size", "name": "Size", "slug": "size", "git_remotes": []},
    )
    assert response.status_code == 201


def test_validation_error_body_does_not_leak_internals():
    client = TestClient(app)
    response = client.post("/projects", json={"org_id": "x"})  # missing name/slug
    assert response.status_code == 422
    body = response.text
    assert "Traceback" not in body
    assert "SELECT" not in body
    assert "/Users/" not in body
    assert ".worktrees" not in body


def test_stable_error_response_redacts_sensitive_values():
    import json

    response = stable_error_response(
        RuntimeError("Authorization: Bearer supersecrettoken failed on SELECT * FROM secrets")
    )
    assert response.status_code == 500
    payload = json.loads(response.body)["detail"]
    assert payload["code"] == "INTERNAL_ERROR"
    assert "supersecrettoken" not in payload["redacted_reason"]
    assert "***REDACTED***" in payload["redacted_reason"]


def test_error_responses_never_echo_authorization_header():
    client = TestClient(app)
    response = client.post(
        "/projects",
        headers={"Authorization": "Bearer leak-me-token"},
        json={"org_id": "x"},
    )
    assert "leak-me-token" not in response.text


def test_cors_preflight_from_allowed_origin_succeeds():
    client = TestClient(app)
    response = client.options(
        "/projects",
        headers={
            "Origin": "http://127.0.0.1:13140",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:13140"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_from_disallowed_origin_rejected():
    client = TestClient(app)
    response = client.options(
        "/projects",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_never_uses_wildcard():
    import os

    os.environ["AGORA_ALLOWED_ORIGINS"] = "https://agora.example.com"
    from apps.api.main import app as fresh_app

    # The middleware list is fixed at import time; assert the configured origins
    # never include "*" by checking the response header for the configured origin.
    client = TestClient(fresh_app)
    response = client.options(
        "/projects",
        headers={
            "Origin": "https://agora.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    allowed = response.headers.get("access-control-allow-origin", "")
    assert allowed != "*"
