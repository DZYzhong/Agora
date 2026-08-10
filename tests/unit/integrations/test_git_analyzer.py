from pathlib import Path

from packages.integrations.git.analyzer import analyze_repository


def test_analyze_repository_detects_readme_modules_and_tests():
    result = analyze_repository(Path("tests/fixtures/sample_repo"))

    assert result.project_summary.startswith("Payment Service")
    assert "src/refund" in result.modules
    assert result.test_paths == ["tests/refund.test.ts"]
    assert "package.json" in result.dependency_files
