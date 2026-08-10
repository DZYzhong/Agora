from pathlib import Path

from packages.integrations.git.analyzer import RepositoryAnalysis, analyze_repository


def analyze_local_repo(repo_path: Path) -> RepositoryAnalysis:
    return analyze_repository(repo_path)
