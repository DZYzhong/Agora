from fastapi.testclient import TestClient

from apps.api.main import app


def test_initialize_local_records_completed_initialization_job():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_init_jobs",
            "name": "Initialization Jobs",
            "slug": "initialization-jobs",
            "git_remotes": ["git@example.com:initialization-jobs.git"],
        },
    ).json()

    init_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert init_response.status_code == 200
    init_body = init_response.json()
    assert init_body["job_id"]
    assert init_body["status"] == "completed"
    assert init_body["asset_count"] > 0

    jobs_response = client.get(f"/projects/{project['id']}/initialization-jobs")

    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert jobs[0]["id"] == init_body["job_id"]
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["repo_path"] == "tests/fixtures/sample_repo"
    assert jobs[0]["asset_count"] == init_body["asset_count"]
    assert jobs[0]["error"] is None


def test_initialize_local_records_failed_initialization_job_when_missing_remote(tmp_path):
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_init_jobs_failed",
            "name": "Initialization Jobs Failed",
            "slug": "initialization-jobs-failed",
            "git_remotes": [],
        },
    ).json()

    init_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(tmp_path / "missing_repo")},
    )

    assert init_response.status_code == 400

    jobs_response = client.get(f"/projects/{project['id']}/initialization-jobs")

    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert jobs[0]["status"] == "failed"
    assert "no Git remote" in jobs[0]["error"]
    assert jobs[0]["asset_count"] == 0
