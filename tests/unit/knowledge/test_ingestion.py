from pathlib import Path

from packages.integrations.git.analyzer import analyze_repository
from packages.knowledge.ingestion import assets_from_repository_analysis


def test_repository_analysis_generates_assets():
    analysis = analyze_repository(Path("tests/fixtures/sample_repo"))

    assets = assets_from_repository_analysis(
        org_id="org_1",
        project_id="proj_1",
        repo_path=Path("tests/fixtures/sample_repo"),
        analysis=analysis,
    )

    titles = {asset.title for asset in assets}
    assert "README.md" in titles
    assert "src/refund" in titles
    assert "src/refund/service.ts" in titles
    assert any(asset.type == "module" for asset in assets)


def test_repository_analysis_generates_java_source_assets(tmp_path):
    repo = tmp_path / "java_repo"
    (repo / "src/main/java/com/acme").mkdir(parents=True)
    (repo / "pom.xml").write_text("<project />", encoding="utf-8")
    (repo / "src/main/java/com/acme/App.java").write_text("class App {}", encoding="utf-8")
    analysis = analyze_repository(repo)

    assets = assets_from_repository_analysis(
        org_id="org_1",
        project_id="proj_1",
        repo_path=repo,
        analysis=analysis,
    )

    titles = {asset.title for asset in assets}
    assert "pom.xml" in titles
    assert "src/main/java/com/acme/App.java" in titles
