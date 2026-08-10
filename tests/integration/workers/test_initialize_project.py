from pathlib import Path

from apps.workers.workflows.initialize_project import initialize_project_from_local_repo


def test_initialize_project_from_local_repo_creates_assets():
    result = initialize_project_from_local_repo(
        org_id="org_1",
        project_id="proj_1",
        repo_path=Path("tests/fixtures/sample_repo"),
    )

    assert result.asset_count > 0
    assert "src/refund" in result.modules
