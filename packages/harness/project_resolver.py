from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectResolution:
    project: object | None
    clarification: str | None = None


class ProjectResolver:
    def __init__(self, core):
        self.core = core

    def resolve(self, *, repo_remote: str | None) -> ProjectResolution:
        if not repo_remote:
            return ProjectResolution(project=None, clarification="Repository remote is required to resolve the Agora project.")
        project = self.core.find_project_by_git_remote(repo_remote)
        if project is None:
            return ProjectResolution(project=None, clarification=f"No Agora project is bound to remote {repo_remote}.")
        return ProjectResolution(project=project)
