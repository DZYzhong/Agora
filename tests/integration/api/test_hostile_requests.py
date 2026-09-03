"""Hostile-request regression: stable, non-500, non-escalating errors.

Covers the PR1/PR5 "attack scenario regression" outcome at the API level:
oversized bodies, malformed JSON, unknown/encoded paths, null bytes and
path-traversal attempts must yield stable JSON errors (never a 500, never
file disclosure).
"""

import json

from fastapi.testclient import TestClient

from apps.api.main import app


def _client():
    return TestClient(app)


def _assert_stable_error(response, *, allowed=(400, 404, 413, 422)):
    assert response.status_code in allowed, response.text
    try:
        json.loads(response.text)
    except json.JSONDecodeError as exc:  # pragma: no cover - fail loudly
        raise AssertionError(f"non-JSON error body: {response.text!r}") from exc


def test_oversized_body_is_413_not_500():
    response = _client().post(
        "/projects",
        json={},
        headers={"content-length": str(2 * 1024 * 1024)},
    )
    # content-length alone triggers BodyLimitMiddleware before parsing.
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "PAYLOAD_TOO_LARGE"


def test_malformed_json_is_stable_error():
    response = _client().post(
        "/auth/login",
        content=b"{not json",
        headers={"content-type": "application/json"},
    )
    _assert_stable_error(response, allowed=(400, 422))
    assert response.status_code != 500


def test_unknown_path_is_json_404():
    response = _client().get("/no-such-route-xyz")
    assert response.status_code == 404
    json.loads(response.text)


def test_null_byte_path_is_rejected_at_transport():
    # httpx refuses to send a control character in the URL, so the request
    # never reaches the server — an acceptable transport-level rejection.
    import pytest

    try:
        from httpx2 import InvalidURL
    except ImportError:  # pragma: no cover - library version variance
        from httpx import InvalidURL

    with pytest.raises(InvalidURL):
        _client().get("/projects/\x00/status")


def test_path_traversal_attempts_do_not_escape_to_files():
    client = _client()
    attempts = [
        "/projects/../../etc/passwd",
        "/projects/%2e%2e/%2e%2e/etc/passwd",
        "/projects/..%2f..%2fetc%2fpasswd",
    ]
    for path in attempts:
        response = client.get(path)
        assert response.status_code in (404, 422), path
        assert "root:" not in response.text, f"file disclosure via {path}"


def test_wildcard_and_deep_query_paths_are_stable():
    client = _client()
    for path in ["/projects/*", "/projects/{%s}" % ("x" * 400), "/health?x=%00"]:
        response = client.get(path)
        assert response.status_code in (200, 404, 422), path
