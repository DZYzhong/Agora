from pathlib import Path

from packages.integrations.git.analyzer import analyze_repository


def test_analyze_repository_detects_readme_modules_and_tests():
    result = analyze_repository(Path("tests/fixtures/sample_repo"))

    assert result.project_summary.startswith("Payment Service")
    assert "src/refund" in result.modules
    assert result.test_paths == ["tests/refund.test.ts"]
    assert "package.json" in result.dependency_files


def test_analyze_repository_detects_java_maven_source_files(tmp_path):
    repo = tmp_path / "java_repo"
    (repo / "src/main/java/com/acme").mkdir(parents=True)
    (repo / "src/test/java/com/acme").mkdir(parents=True)
    (repo / "target/classes").mkdir(parents=True)
    (repo / ".git/objects").mkdir(parents=True)
    (repo / "pom.xml").write_text("<project />", encoding="utf-8")
    (repo / "src/main/java/com/acme/App.java").write_text("class App {}", encoding="utf-8")
    (repo / "src/test/java/com/acme/AppTest.java").write_text("class AppTest {}", encoding="utf-8")
    (repo / "target/classes/App.class").write_text("compiled", encoding="utf-8")
    (repo / ".git/config").write_text("[core]", encoding="utf-8")

    result = analyze_repository(repo)

    assert "src/main" in result.modules
    assert "src/main/java/com/acme/App.java" in result.source_files
    assert "src/test/java/com/acme/AppTest.java" in result.test_paths
    assert "target/classes/App.class" not in result.source_files
    assert ".git/config" not in result.source_files
