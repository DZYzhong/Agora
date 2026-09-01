import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine, get_keyword_index, get_vector_index
from apps.api.main import app
from packages.core.models import AssetModel
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.initialization_jobs import InitializationJobRepository
from packages.core.repositories.projects import ProjectRepository

HUMAN_TOKEN = "init-human-token-secret-value"
AGENT_TOKEN = "init-agent-token-secret-value"
CI_TOKEN = "init-ci-token-secret-value"


@pytest.fixture
def sample_local_repo(local_init_root):
    repo = local_init_root / "sample_repo"
    shutil.copytree("tests/fixtures/sample_repo", repo)
    return repo


def _configure_authenticated_runtime(monkeypatch, *, environment: str, local_init_root=None):
    monkeypatch.setenv("AGORA_ENV", environment)
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", CI_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "init-security-org")
    if local_init_root is None:
        monkeypatch.delenv("AGORA_LOCAL_INIT_ROOT", raising=False)
    else:
        monkeypatch.setenv("AGORA_LOCAL_INIT_ROOT", str(local_init_root))


def _auth_headers():
    return {"Authorization": f"Bearer {HUMAN_TOKEN}"}


def _create_authenticated_project(client, *, slug: str):
    response = client.post(
        "/projects",
        headers=_auth_headers(),
        json={
            "org_id": "ignored-org",
            "name": slug.replace("-", " ").title(),
            "slug": slug,
            "git_remotes": [],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_git_repo(repo):
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text("# Allowed Repository\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "init@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Init Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)


def _seed_failed_initialization_job(*, project_id: str, org_id: str, repo_path: str):
    with sessionmaker(bind=get_engine())() as session:
        job = InitializationJobRepository(session).create(
            org_id=org_id,
            project_id=project_id,
            repo_path=repo_path,
            status="failed",
        )
        session.commit()
        return job.id


def test_production_initialize_and_retry_are_route_equivalent_404(monkeypatch, tmp_path):
    _configure_authenticated_runtime(monkeypatch, environment="production")

    with TestClient(app) as client:
        project = _create_authenticated_project(client, slug="production-local-init-hidden")
        job_id = _seed_failed_initialization_job(
            project_id=project["id"],
            org_id=project["org_id"],
            repo_path=str(tmp_path / "stored-repository"),
        )
        missing_route = client.post("/route-that-does-not-exist", headers=_auth_headers())
        initialize = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
            json={"repo_path": str(tmp_path / "candidate")},
        )
        retry = client.post(
            f"/projects/{project['id']}/initialization-jobs/{job_id}/retry",
            headers=_auth_headers(),
        )
        unauthenticated_initialize = client.post(
            f"/projects/{project['id']}/initialize-local",
            json={"repo_path": str(tmp_path / "candidate")},
        )
        invalid_body_initialize = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
            json={},
        )
        malformed_initialize = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers={**_auth_headers(), "Content-Type": "application/json"},
            content="{",
        )
        get_initialize = client.get(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
        )
        options_initialize = client.options(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
        )
        unauthenticated_retry = client.post(
            f"/projects/{project['id']}/initialization-jobs/{job_id}/retry"
        )
        get_retry = client.get(
            f"/projects/{project['id']}/initialization-jobs/{job_id}/retry",
            headers=_auth_headers(),
        )
        options_retry = client.options(
            f"/projects/{project['id']}/initialization-jobs/{job_id}/retry",
            headers=_auth_headers(),
        )
        openapi = client.get("/openapi.json")

    assert initialize.status_code == missing_route.status_code == 404
    assert retry.status_code == missing_route.status_code
    assert unauthenticated_initialize.status_code == missing_route.status_code
    assert invalid_body_initialize.status_code == missing_route.status_code
    assert malformed_initialize.status_code == missing_route.status_code
    assert get_initialize.status_code == missing_route.status_code
    assert options_initialize.status_code == missing_route.status_code
    assert unauthenticated_retry.status_code == missing_route.status_code
    assert get_retry.status_code == missing_route.status_code
    assert options_retry.status_code == missing_route.status_code
    assert initialize.json() == missing_route.json()
    assert retry.json() == missing_route.json()
    assert unauthenticated_initialize.json() == missing_route.json()
    assert invalid_body_initialize.json() == missing_route.json()
    assert malformed_initialize.json() == missing_route.json()
    assert get_initialize.json() == missing_route.json()
    assert options_initialize.json() == missing_route.json()
    assert unauthenticated_retry.json() == missing_route.json()
    assert get_retry.json() == missing_route.json()
    assert options_retry.json() == missing_route.json()
    assert initialize.headers["x-request-id"]
    assert retry.headers["x-request-id"]
    assert unauthenticated_initialize.headers["x-request-id"]
    assert invalid_body_initialize.headers["x-request-id"]
    assert malformed_initialize.headers["x-request-id"]
    assert get_initialize.headers["x-request-id"]
    assert options_initialize.headers["x-request-id"]
    assert unauthenticated_retry.headers["x-request-id"]
    assert get_retry.headers["x-request-id"]
    assert options_retry.headers["x-request-id"]
    assert "allow" not in get_initialize.headers
    assert "allow" not in options_initialize.headers
    assert "allow" not in get_retry.headers
    assert "allow" not in options_retry.headers
    assert openapi.status_code == 200
    assert "/projects/{project_id}/initialize-local" not in openapi.json()["paths"]
    assert (
        "/projects/{project_id}/initialization-jobs/{job_id}/retry"
        not in openapi.json()["paths"]
    )


@pytest.mark.parametrize("environment", ["development", "test"])
def test_initialize_without_local_root_returns_stable_disabled_error(
    monkeypatch, tmp_path, environment
):
    _configure_authenticated_runtime(monkeypatch, environment=environment)

    with TestClient(app) as client:
        project = _create_authenticated_project(client, slug=f"{environment}-local-init-disabled")
        response = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
            json={"repo_path": str(tmp_path / "candidate")},
        )
        jobs = client.get(
            f"/projects/{project['id']}/initialization-jobs", headers=_auth_headers()
        )

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "LOCAL_INIT_DISABLED",
        "message": "Local repository initialization is disabled",
    }
    assert jobs.json() == []


@pytest.mark.parametrize("candidate_kind", ["outside", "dotdot", "symlink"])
def test_initialize_rejects_paths_that_escape_local_root(monkeypatch, tmp_path, candidate_kind):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _create_git_repo(outside)
    if candidate_kind == "outside":
        candidate = outside
    elif candidate_kind == "dotdot":
        candidate = root / ".." / "outside"
    else:
        candidate = root / "repository-link"
        candidate.symlink_to(outside, target_is_directory=True)
    _configure_authenticated_runtime(
        monkeypatch, environment="development", local_init_root=root
    )

    with TestClient(app) as client:
        project = _create_authenticated_project(client, slug=f"reject-{candidate_kind}-escape")
        response = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
            json={"repo_path": str(candidate)},
        )
        jobs = client.get(
            f"/projects/{project['id']}/initialization-jobs", headers=_auth_headers()
        )

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "LOCAL_INIT_PATH_FORBIDDEN",
        "message": "Repository path is outside the allowed local initialization root",
    }
    assert str(candidate) not in response.text
    assert str(root) not in response.text
    assert jobs.json() == []


def test_retry_revalidates_stored_repository_path_against_current_root(monkeypatch, tmp_path):
    original_root = tmp_path / "original-root"
    current_root = tmp_path / "current-root"
    original_root.mkdir()
    current_root.mkdir()
    stored_repo = original_root / "repository"
    _create_git_repo(stored_repo)
    _configure_authenticated_runtime(
        monkeypatch, environment="development", local_init_root=original_root
    )

    with TestClient(app) as client:
        project = _create_authenticated_project(client, slug="retry-current-root")
        job_id = _seed_failed_initialization_job(
            project_id=project["id"],
            org_id=project["org_id"],
            repo_path=str(stored_repo),
        )
        monkeypatch.setenv("AGORA_LOCAL_INIT_ROOT", str(current_root))

        response = client.post(
            f"/projects/{project['id']}/initialization-jobs/{job_id}/retry",
            headers=_auth_headers(),
        )
        jobs = client.get(
            f"/projects/{project['id']}/initialization-jobs", headers=_auth_headers()
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "LOCAL_INIT_PATH_FORBIDDEN"
    assert str(stored_repo) not in response.text
    assert str(current_root) not in response.text
    assert len(jobs.json()) == 1


def test_authenticated_allowed_git_repository_inside_narrow_root_initializes(
    monkeypatch, tmp_path
):
    root = tmp_path / "allowed"
    root.mkdir()
    repo = root / "repository"
    _create_git_repo(repo)
    _configure_authenticated_runtime(
        monkeypatch, environment="development", local_init_root=root
    )

    with TestClient(app) as client:
        project = _create_authenticated_project(client, slug="allowed-local-init")
        response = client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth_headers(),
            json={"repo_path": str(repo)},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["asset_count"] > 0


def test_initialize_local_records_completed_initialization_job(
    authenticated_client, sample_local_repo
):
    client = authenticated_client
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
        json={"repo_path": str(sample_local_repo)},
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
    assert jobs[0]["repo_path"] == str(sample_local_repo)
    assert jobs[0]["asset_count"] == init_body["asset_count"]
    assert jobs[0]["error"] is None


def test_initialize_local_can_be_repeated_without_duplicate_assets(
    authenticated_client, sample_local_repo
):
    client = authenticated_client
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
        json={"repo_path": str(sample_local_repo)},
    )
    second = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(sample_local_repo)},
    )
    assets = client.get(f"/projects/{project['id']}/assets").json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["asset_count"] == second.json()["asset_count"]
    assert len(assets) == first.json()["asset_count"]


def test_reinitialize_prunes_git_assets_removed_from_repository(
    authenticated_client, local_init_root
):
    client = authenticated_client
    repo = local_init_root / "repo"
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


def test_initialize_local_records_failed_initialization_job_when_missing_remote(
    authenticated_client, local_init_root
):
    client = authenticated_client
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
        json={"repo_path": str(local_init_root / "missing_repo")},
    )

    assert init_response.status_code == 400

    jobs_response = client.get(f"/projects/{project['id']}/initialization-jobs")

    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert jobs[0]["status"] == "failed"
    assert "no Git remote" in jobs[0]["error"]
    assert jobs[0]["asset_count"] == 0


def test_retry_failed_initialization_job_uses_previous_repo_path(
    authenticated_client, local_init_root
):
    client = authenticated_client
    missing_repo = local_init_root / "missing_repo"
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


def test_initialize_failure_after_first_asset_leaves_only_failed_job(
    monkeypatch, authenticated_client, sample_local_repo
):
    client = authenticated_client
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
        json={"repo_path": str(sample_local_repo)},
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


def test_retry_failure_after_first_asset_leaves_failed_jobs_without_assets(
    monkeypatch, authenticated_client, local_init_root
):
    client = authenticated_client
    repo = local_init_root / "retry_repo"
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


def test_successful_initialize_indexes_only_after_database_commit(
    monkeypatch, authenticated_client, sample_local_repo
):
    client = authenticated_client
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
        json={"repo_path": str(sample_local_repo)},
    )

    assert response.status_code == 200
    assert len(indexed_asset_ids) == response.json()["asset_count"]


def test_initialize_index_failure_returns_completed_job_with_pending_rebuild_warning(
    monkeypatch, authenticated_client_no_raise, sample_local_repo
):
    client = authenticated_client_no_raise
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
        json={"repo_path": str(sample_local_repo)},
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


def test_unexpected_execution_exception_marks_committed_job_failed(
    monkeypatch, authenticated_client_no_raise, sample_local_repo
):
    client = authenticated_client_no_raise
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
        json={"repo_path": str(sample_local_repo)},
    )

    assert response.status_code == 500
    jobs = client.get(f"/projects/{project['id']}/initialization-jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"
    assert "injected execution read failure" in jobs[0]["error"]
