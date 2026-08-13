from dataclasses import dataclass
import os
from pathlib import Path

MAX_SOURCE_FILE_BYTES = 128_000


DEPENDENCY_FILES = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "go.mod",
    "Cargo.toml",
]

SOURCE_EXTENSIONS = {
    ".css",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".md",
    ".py",
    ".rs",
    ".scss",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".next",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
    "__pycache__",
}


@dataclass(frozen=True)
class RepositoryAnalysis:
    project_summary: str
    modules: list[str]
    test_paths: list[str]
    dependency_files: list[str]
    readme_path: str | None
    source_files: list[str]
    scanned_file_count: int = 0
    skipped_file_count: int = 0
    warnings: list[str] | None = None


def analyze_repository(repo_path: Path) -> RepositoryAnalysis:
    readme = _find_readme(repo_path)
    source_scan = _scan_source_files(repo_path)
    return RepositoryAnalysis(
        project_summary=_summarize_readme(readme) if readme else repo_path.name,
        modules=_find_modules(repo_path),
        test_paths=_find_tests(source_scan.source_files),
        dependency_files=_find_dependency_files(repo_path),
        readme_path=_relative(readme, repo_path) if readme else None,
        source_files=source_scan.source_files,
        scanned_file_count=source_scan.scanned_file_count,
        skipped_file_count=source_scan.skipped_file_count,
        warnings=source_scan.warnings,
    )


@dataclass(frozen=True)
class SourceFileScan:
    source_files: list[str]
    scanned_file_count: int
    skipped_file_count: int
    warnings: list[str]


def _find_readme(repo_path: Path) -> Path | None:
    for name in ("README.md", "README.rst", "README.txt"):
        path = repo_path / name
        if path.exists():
            return path
    return None


def _summarize_readme(readme: Path) -> str:
    lines = [line.strip() for line in readme.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return readme.stem
    heading = lines[0].lstrip("#").strip()
    paragraph = next((line for line in lines[1:] if not line.startswith("#")), "")
    return f"{heading}. {paragraph}".strip()


def _find_modules(repo_path: Path) -> list[str]:
    src = repo_path / "src"
    if not src.exists():
        return []
    modules = []
    for child in sorted(src.iterdir()):
        if child.is_dir():
            modules.append(_relative(child, repo_path))
    return modules


def _find_tests(source_files: list[str]) -> list[str]:
    return [
        relative_path
        for relative_path in source_files
        if _is_test_path(relative_path)
    ]


def _find_dependency_files(repo_path: Path) -> list[str]:
    return [name for name in DEPENDENCY_FILES if (repo_path / name).exists()]


def _find_source_files(repo_path: Path) -> list[str]:
    return _scan_source_files(repo_path).source_files


def _scan_source_files(repo_path: Path) -> SourceFileScan:
    files: list[str] = []
    skipped: list[str] = []
    ignored_dirs: set[str] = set()
    scanned_file_count = 0
    for root, dir_names, file_names in os.walk(repo_path):
        root_path = Path(root)
        kept_dirs = []
        for dir_name in sorted(dir_names):
            relative_dir = (root_path / dir_name).relative_to(repo_path).as_posix()
            if dir_name in IGNORED_DIRS:
                ignored_dirs.add(relative_dir)
            else:
                kept_dirs.append(dir_name)
        dir_names[:] = kept_dirs

        for file_name in sorted(file_names):
            path = root_path / file_name
            scanned_file_count += 1
            relative_path = _relative(path, repo_path)
            skip_reason = _skip_reason(path)
            if skip_reason:
                skipped.append(f"{relative_path} ({skip_reason})")
                continue
            files.append(relative_path)
    warnings = []
    if ignored_dirs:
        warnings.append(f"Ignored directories: {', '.join(sorted(ignored_dirs)[:8])}")
    if skipped:
        warnings.append(f"Skipped {len(skipped)} files during repository analysis: {', '.join(skipped[:5])}")
    return SourceFileScan(
        source_files=files,
        scanned_file_count=scanned_file_count,
        skipped_file_count=len(skipped),
        warnings=warnings,
    )


def _skip_reason(path: Path) -> str | None:
    if path.stat().st_size > MAX_SOURCE_FILE_BYTES:
        return f"larger than {MAX_SOURCE_FILE_BYTES} bytes"
    if path.suffix.lower() not in SOURCE_EXTENSIONS:
        return "unsupported extension"
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "not valid UTF-8 text"
    return None


def _is_ignored(path: Path, repo_path: Path) -> bool:
    relative_parts = path.relative_to(repo_path).parts
    return any(part in IGNORED_DIRS for part in relative_parts)


def _is_test_path(relative_path: str) -> bool:
    path = relative_path.lower()
    return (
        path.startswith("tests/")
        or "/tests/" in path
        or path.startswith("src/test/")
        or "/src/test/" in path
        or path.endswith("_test.py")
        or path.endswith(".test.ts")
        or path.endswith(".test.tsx")
        or path.endswith(".spec.ts")
        or path.endswith(".spec.tsx")
    )


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
