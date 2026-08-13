from hashlib import sha256

from packages.domain.schemas import AssetCreate
from packages.integrations.git.analyzer import RepositoryAnalysis


def generate_project_overview_asset(
    *,
    org_id: str,
    project_id: str,
    analysis: RepositoryAnalysis,
) -> AssetCreate:
    source_files = _sample_paths(analysis.source_files, limit=12)
    test_paths = _sample_paths(analysis.test_paths, limit=8)
    modules = _sample_paths(analysis.modules, limit=10)
    dependency_files = _sample_paths(analysis.dependency_files, limit=8)

    sections = [
        "# Project Overview",
        "",
        f"Summary: {analysis.project_summary}",
        _format_section("Modules", modules),
        _format_section("Dependency files", dependency_files),
        _format_section("Source paths", source_files),
        _format_section("Test paths", test_paths),
    ]
    if analysis.readme_path:
        sections.append(f"README: {analysis.readme_path}")

    content = "\n".join(section for section in sections if section)
    content_hash = sha256(content.encode("utf-8")).hexdigest()
    return AssetCreate(
        org_id=org_id,
        project_id=project_id,
        type="project_overview",
        source="agora",
        source_uri="agora://project-overview",
        title="Project Overview",
        content=content,
        summary=analysis.project_summary,
        metadata={
            "module_count": len(analysis.modules),
            "dependency_file_count": len(analysis.dependency_files),
            "source_count": len(analysis.source_files),
            "test_count": len(analysis.test_paths),
            "readme_path": analysis.readme_path,
            "scanned_file_count": analysis.scanned_file_count,
            "skipped_file_count": analysis.skipped_file_count,
        },
        content_hash=content_hash,
    )


def _format_section(title: str, values: list[str]) -> str:
    if not values:
        return f"{title}: none detected"
    return f"{title}:\n" + "\n".join(f"- {value}" for value in values)


def _sample_paths(paths: list[str], *, limit: int) -> list[str]:
    return paths[:limit]
