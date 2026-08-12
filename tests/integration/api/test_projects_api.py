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


def test_archive_project_hides_it_from_default_project_list():
    client = TestClient(app)
    keep = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Keep",
            "slug": "keep",
            "git_remotes": ["git@example.com:keep.git"],
        },
    ).json()
    archived = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Archive",
            "slug": "archive",
            "git_remotes": ["git@example.com:archive.git"],
        },
    ).json()

    archive_response = client.post(f"/projects/{archived['id']}/archive")

    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    active_projects = client.get("/projects").json()
    assert [project["id"] for project in active_projects] == [keep["id"]]
    all_projects = client.get("/projects?include_archived=true").json()
    assert {project["id"] for project in all_projects} == {keep["id"], archived["id"]}
