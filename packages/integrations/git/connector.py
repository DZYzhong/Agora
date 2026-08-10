from pathlib import Path

from packages.integrations.git.analyzer import RepositoryAnalysis, analyze_repository


class LocalGitConnector:
    def analyze(self, repo_path: Path) -> RepositoryAnalysis:
        return analyze_repository(repo_path)
