from dataclasses import dataclass
from pathlib import Path


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


def analyze_repository(repo_path: Path) -> RepositoryAnalysis:
    readme = _find_readme(repo_path)
    return RepositoryAnalysis(
        project_summary=_summarize_readme(readme) if readme else repo_path.name,
        modules=_find_modules(repo_path),
        test_paths=_find_tests(repo_path),
        dependency_files=_find_dependency_files(repo_path),
        readme_path=_relative(readme, repo_path) if readme else None,
        source_files=_find_source_files(repo_path),
    )


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


def _find_tests(repo_path: Path) -> list[str]:
    return [
        relative_path
        for relative_path in _find_source_files(repo_path)
        if _is_test_path(relative_path)
    ]


def _find_dependency_files(repo_path: Path) -> list[str]:
    return [name for name in DEPENDENCY_FILES if (repo_path / name).exists()]


def _find_source_files(repo_path: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(repo_path.rglob("*")):
        if not path.is_file() or _is_ignored(path, repo_path):
            continue
        if path.suffix.lower() in SOURCE_EXTENSIONS:
            files.append(_relative(path, repo_path))
    return files


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
