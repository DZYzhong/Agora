from packages.integrations.git.analyzer import RepositoryAnalysis
from packages.knowledge.project_overview import generate_project_overview_asset


def test_generate_project_overview_asset_summarizes_repo_structure():
    analysis = RepositoryAnalysis(
        project_summary="Payment service. Handles refunds.",
        modules=["src/refund", "src/payment"],
        test_paths=["tests/test_refund.py"],
        dependency_files=["pyproject.toml"],
        readme_path="README.md",
        source_files=["src/refund/service.py", "src/payment/api.py", "tests/test_refund.py"],
    )

    asset = generate_project_overview_asset(org_id="org_1", project_id="proj_1", analysis=analysis)

    assert asset.type == "project_overview"
    assert asset.title == "Project Overview"
    assert "Payment service" in asset.content
    assert "src/refund" in asset.content
    assert "pyproject.toml" in asset.content
    assert "tests/test_refund.py" in asset.content
    assert asset.metadata["source_count"] == 3
