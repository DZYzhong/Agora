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
    assert result.assets[0].type == "project_overview"
    assert result.assets[0].title == "Project Overview"


def test_initialize_project_from_local_repo_returns_analysis_warnings(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "node_modules/pkg").mkdir(parents=True)
    (repo / "src/app.py").write_text("print('ok')", encoding="utf-8")
    (repo / "node_modules/pkg/index.js").write_text("ignored", encoding="utf-8")

    result = initialize_project_from_local_repo(
        org_id="org_1",
        project_id="proj_1",
        repo_path=repo,
    )

    assert result.asset_count > 0
    assert result.warnings
    assert any("Ignored directories: node_modules" in warning for warning in result.warnings)
