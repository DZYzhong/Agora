from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine, get_keyword_index, get_vector_index
from apps.api.main import app
from packages.core.models import AssetModel
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.initialization_jobs import InitializationJobRepository
from packages.core.repositories.projects import ProjectRepository


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


def test_reinitialize_prunes_git_assets_removed_from_repository(tmp_path):
    client = TestClient(app)
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Prune Repo\n\nPrune deleted files.", encoding="utf-8")
    (repo / "src/app.py").write_text("print('keep')", encoding="utf-8")
    (repo / "src/removed.py").write_text("print('remove')", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_prune",
            "name": "Prune",
            "slug": "prune",
            "git_remotes": [],
        },
    ).json()

    first = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(repo)},
    )
    assert first.status_code == 200
    (repo / "src/removed.py").unlink()

    second = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(repo)},
    )

    assert second.status_code == 200
    assets = client.get(f"/projects/{project['id']}/assets").json()
    source_uris = {asset["source_uri"] for asset in assets}
    assert "src/app.py" in source_uris
    assert "src/removed.py" not in source_uris


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


def test_initialize_failure_after_first_asset_leaves_only_failed_job(monkeypatch):
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_atomic_init",
            "name": "Atomic Initialization",
            "slug": "atomic-initialization",
            "git_remotes": [],
        },
    ).json()
    original_upsert = AssetRepository.upsert_by_source_uri
    calls = 0

    def fail_after_first_asset(self, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected asset write failure")
        return original_upsert(self, **kwargs)

    monkeypatch.setattr(AssetRepository, "upsert_by_source_uri", fail_after_first_asset)

    response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert response.status_code == 500
    assert client.get(f"/projects/{project['id']}/assets").json() == []
    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"
    assert jobs[0]["asset_count"] == 0
    assert "injected asset write failure" in jobs[0]["error"]
    assert get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"]) == []
    assert get_vector_index()._assets == []


def test_retry_failure_after_first_asset_leaves_failed_jobs_without_assets(monkeypatch, tmp_path):
    client = TestClient(app)
    repo = tmp_path / "retry_repo"
    project = client.post(
        "/projects",
        json={
            "org_id": "org_atomic_retry",
            "name": "Atomic Retry",
            "slug": "atomic-retry",
            "git_remotes": [],
        },
    ).json()
    first_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(repo)},
    )
    assert first_response.status_code == 400
    first_job = client.get(f"/projects/{project['id']}/initialization-jobs").json()[0]
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Atomic Retry", encoding="utf-8")
    (repo / "src/app.py").write_text("print('retry')", encoding="utf-8")
    original_upsert = AssetRepository.upsert_by_source_uri
    calls = 0

    def fail_after_first_asset(self, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected retry asset failure")
        return original_upsert(self, **kwargs)

    monkeypatch.setattr(AssetRepository, "upsert_by_source_uri", fail_after_first_asset)

    response = client.post(f"/projects/{project['id']}/initialization-jobs/{first_job['id']}/retry")

    assert response.status_code == 500
    assert client.get(f"/projects/{project['id']}/assets").json() == []
    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert len(jobs) == 2
    assert [job["status"] for job in jobs] == ["failed", "failed"]
    assert "injected retry asset failure" in jobs[0]["error"]
    assert get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"]) == []
    assert get_vector_index()._assets == []


def test_successful_initialize_indexes_only_after_database_commit(monkeypatch):
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_atomic_index",
            "name": "Atomic Index",
            "slug": "atomic-index",
            "git_remotes": [],
        },
    ).json()
    keyword_index = get_keyword_index()
    original_index_asset = keyword_index.index_asset
    indexed_asset_ids = []

    def assert_database_committed(asset_id, asset):
        with sessionmaker(bind=get_engine())() as session:
            assert session.get(AssetModel, asset_id) is not None
            jobs = InitializationJobRepository(session).list_by_project(project["id"])
            assert len(jobs) == 1
            assert jobs[0].status == "completed"
        indexed_asset_ids.append(asset_id)
        original_index_asset(asset_id, asset)

    monkeypatch.setattr(keyword_index, "index_asset", assert_database_committed)

    response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert response.status_code == 200
    assert len(indexed_asset_ids) == response.json()["asset_count"]


def test_initialize_index_failure_returns_completed_job_with_pending_rebuild_warning(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_init_index_failure",
            "name": "Initialization Index Failure",
            "slug": "initialization-index-failure",
            "git_remotes": [],
        },
    ).json()
    keyword_index = get_keyword_index()
    calls = 0

    def fail_first_keyword_index(asset_id, asset):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("keyword index unavailable")

    monkeypatch.setattr(keyword_index, "index_asset", fail_first_keyword_index)

    response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["index_status"] == "pending_rebuild"
    assert any("keyword index unavailable" in warning for warning in body["warnings"])
    assert len(client.get(f"/projects/{project['id']}/assets").json()) == body["asset_count"]
    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["error"] is None


def test_unexpected_execution_exception_marks_committed_job_failed(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_execution_failure",
            "name": "Execution Failure",
            "slug": "execution-failure",
            "git_remotes": [],
        },
    ).json()
    original_get = ProjectRepository.get
    calls = 0

    def fail_execution_read(self, project_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected execution read failure")
        return original_get(self, project_id)

    monkeypatch.setattr(ProjectRepository, "get", fail_execution_read)

    response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert response.status_code == 500
    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"
    assert "injected execution read failure" in jobs[0]["error"]
