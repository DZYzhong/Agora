from fastapi.testclient import TestClient

from apps.api.main import app


def test_create_project_api():
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Payment",
            "slug": "payment",
            "git_remotes": ["git@example.com:payment.git"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Payment"
