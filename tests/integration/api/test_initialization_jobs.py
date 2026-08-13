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


def test_initialize_local_can_be_repeated_without_duplicate_assets():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_reinit",
            "name": "Reinitialize",
            "slug": "reinitialize",
            "git_remotes": ["git@example.com:reinitialize.git"],
        },
    ).json()

    first = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )
    second = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )
    assets = client.get(f"/projects/{project['id']}/assets").json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["asset_count"] == second.json()["asset_count"]
    assert len(assets) == first.json()["asset_count"]


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


def test_retry_failed_initialization_job_uses_previous_repo_path(tmp_path):
    client = TestClient(app)
    missing_repo = tmp_path / "missing_repo"
    project = client.post(
        "/projects",
        json={
            "org_id": "org_retry_init",
            "name": "Retry Initialization",
            "slug": "retry-initialization",
            "git_remotes": [],
        },
    ).json()

    failed_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(missing_repo)},
    )
    assert failed_response.status_code == 400

    (missing_repo / "src").mkdir(parents=True)
    (missing_repo / "README.md").write_text("# Retry Repo\n\nRecovered repository.", encoding="utf-8")
    (missing_repo / "src/app.py").write_text("print('retry')", encoding="utf-8")
    failed_job = client.get(f"/projects/{project['id']}/initialization-jobs").json()[0]

    retry_response = client.post(f"/projects/{project['id']}/initialization-jobs/{failed_job['id']}/retry")

    assert retry_response.status_code == 200
    retry_body = retry_response.json()
    assert retry_body["status"] == "completed"
    assert retry_body["asset_count"] > 0
    assert retry_body["retry_of_job_id"] == failed_job["id"]

    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["repo_path"] == str(missing_repo)
    assert jobs[1]["status"] == "failed"
