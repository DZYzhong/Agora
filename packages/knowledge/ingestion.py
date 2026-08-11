from pathlib import Path

from packages.domain.schemas import AssetCreate
from packages.integrations.git.analyzer import RepositoryAnalysis


def assets_from_repository_analysis(
    *,
    org_id: str,
    project_id: str,
    repo_path: Path,
    analysis: RepositoryAnalysis,
) -> list[AssetCreate]:
    assets: list[AssetCreate] = []

    if analysis.readme_path:
        assets.append(_file_asset(org_id, project_id, repo_path, analysis.readme_path, "doc"))

    indexed_paths = {analysis.readme_path} if analysis.readme_path else set()

    for module_path in analysis.modules:
        module_dir = repo_path / module_path
        assets.append(
            AssetCreate(
                org_id=org_id,
                project_id=project_id,
                type="module",
                source="git",
                source_uri=module_path,
                title=module_path,
                content=_summarize_module(module_dir, repo_path),
                summary=f"Module {module_path}",
                metadata={"path": module_path},
            )
        )

    for dependency_file in analysis.dependency_files:
        if dependency_file != analysis.readme_path:
            assets.append(_file_asset(org_id, project_id, repo_path, dependency_file, "doc", {"kind": "dependency_manifest"}))
            indexed_paths.add(dependency_file)

    for source_file in analysis.source_files:
        if source_file not in indexed_paths:
            assets.append(_file_asset(org_id, project_id, repo_path, source_file, "code_file"))

    return assets


def _file_asset(
    org_id: str,
    project_id: str,
    repo_path: Path,
    relative_path: str,
    asset_type: str,
    metadata: dict | None = None,
) -> AssetCreate:
    path = repo_path / relative_path
    content = path.read_text(encoding="utf-8")
    return AssetCreate(
        org_id=org_id,
        project_id=project_id,
        type=asset_type,
        source="git",
        source_uri=relative_path,
        title=relative_path,
        content=content,
        summary=content.strip().splitlines()[0] if content.strip() else relative_path,
        metadata=metadata or {"path": relative_path},
    )


def _summarize_module(module_dir: Path, repo_path: Path) -> str:
    files = [path.relative_to(repo_path).as_posix() for path in sorted(module_dir.rglob("*")) if path.is_file()]
    return "\n".join(files)
