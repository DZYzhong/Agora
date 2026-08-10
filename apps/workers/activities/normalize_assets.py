from pathlib import Path

from packages.domain.schemas import AssetCreate
from packages.integrations.git.analyzer import RepositoryAnalysis
from packages.knowledge.ingestion import assets_from_repository_analysis


def normalize_repository_assets(
    *,
    org_id: str,
    project_id: str,
    repo_path: Path,
    analysis: RepositoryAnalysis,
) -> list[AssetCreate]:
    return assets_from_repository_analysis(
        org_id=org_id,
        project_id=project_id,
        repo_path=repo_path,
        analysis=analysis,
    )
