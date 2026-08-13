from dataclasses import dataclass, field
from pathlib import Path

from packages.domain.schemas import AssetCreate
from apps.workers.activities.git_sync import analyze_local_repo
from apps.workers.activities.normalize_assets import normalize_repository_assets
from packages.knowledge.project_overview import generate_project_overview_asset


@dataclass(frozen=True)
class InitializeProjectResult:
    asset_count: int
    modules: list[str]
    assets: list[AssetCreate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def initialize_project_from_local_repo(
    *,
    org_id: str,
    project_id: str,
    repo_path: Path,
) -> InitializeProjectResult:
    analysis = analyze_local_repo(repo_path)
    overview_asset = generate_project_overview_asset(
        org_id=org_id,
        project_id=project_id,
        analysis=analysis,
    )
    assets = [overview_asset] + normalize_repository_assets(
        org_id=org_id,
        project_id=project_id,
        repo_path=repo_path,
        analysis=analysis,
    )
    return InitializeProjectResult(
        asset_count=len(assets),
        modules=analysis.modules,
        assets=assets,
        warnings=analysis.warnings or [],
    )
