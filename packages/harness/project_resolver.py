from dataclasses import dataclass

from packages.domain.local_workspace import LocalWorkspaceObservation
from packages.local_connector.sanitization import normalize_repository_identity


@dataclass(frozen=True)
class ProjectResolution:
    project: object | None
    clarification: str | None = None


class ProjectResolver:
    def __init__(self, core):
        self.core = core

    def resolve(
        self,
        *,
        repo_remote: str | None,
        user_message: str | None = None,
        local_observation: LocalWorkspaceObservation | dict | None = None,
    ) -> ProjectResolution:
        projects = self._list_projects()

        observed_identity = _observation_identity(local_observation)
        candidate_remote = repo_remote or (observed_identity.normalized if observed_identity else None)

        if candidate_remote:
            project = self.core.find_project_by_git_remote(candidate_remote)
            if project is not None:
                return ProjectResolution(project=project)

            normalized_remote = _repository_identity(candidate_remote)
            for candidate in reversed(projects):
                if any(_repository_identity(remote) == normalized_remote for remote in candidate.git_remotes or []):
                    return ProjectResolution(project=candidate)

        if user_message:
            message = user_message.lower()
            for candidate in reversed(projects):
                names = [candidate.name.lower(), candidate.slug.lower()]
                if any(name and name in message for name in names):
                    return ProjectResolution(project=candidate)

        if not candidate_remote:
            return ProjectResolution(project=None, clarification="Project name, slug, or repository remote is required to resolve the Agora project.")
        project = None
        return ProjectResolution(project=project, clarification=f"No Agora project is bound to repository {candidate_remote}.")

    def _list_projects(self):
        if hasattr(self.core, "list_projects"):
            return self.core.list_projects()
        return []


def _normalize_remote(remote: str) -> str:
    normalized = remote.strip().lower()
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    if "://" in normalized:
        scheme, rest = normalized.split("://", 1)
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        normalized = f"{scheme}://{rest}"
    return normalized.rstrip("/")


def _repository_identity(remote: str | None) -> str | None:
    identity = normalize_repository_identity(remote)
    return identity.normalized if identity else (_normalize_remote(remote) if remote else None)


def _observation_identity(local_observation: LocalWorkspaceObservation | dict | None):
    if local_observation is None:
        return None
    observation = (
        local_observation
        if isinstance(local_observation, LocalWorkspaceObservation)
        else LocalWorkspaceObservation.model_validate(local_observation)
    )
    return observation.repository
