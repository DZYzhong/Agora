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


@dataclass(frozen=True)
class RepositoryAnalysis:
    project_summary: str
    modules: list[str]
    test_paths: list[str]
    dependency_files: list[str]
    readme_path: str | None


def analyze_repository(repo_path: Path) -> RepositoryAnalysis:
    readme = _find_readme(repo_path)
    return RepositoryAnalysis(
        project_summary=_summarize_readme(readme) if readme else repo_path.name,
        modules=_find_modules(repo_path),
        test_paths=_find_tests(repo_path),
        dependency_files=_find_dependency_files(repo_path),
        readme_path=_relative(readme, repo_path) if readme else None,
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
    tests_dir = repo_path / "tests"
    if not tests_dir.exists():
        return []
    return [
        _relative(path, repo_path)
        for path in sorted(tests_dir.rglob("*"))
        if path.is_file()
    ]


def _find_dependency_files(repo_path: Path) -> list[str]:
    return [name for name in DEPENDENCY_FILES if (repo_path / name).exists()]


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
