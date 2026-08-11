from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from packages.knowledge.context_engine import PlannedContextPack


@dataclass
class FakeProject:
    org_id: str
    name: str
    slug: str
    git_remotes: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class FakeSession:
    org_id: str
    project_id: str
    agent_type: str
    intent: str
    task_id: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


class FakeCore:
    def __init__(self):
        self.projects: list[FakeProject] = []
        self.sessions: list[FakeSession] = []
        self.events: list[dict] = []

    def create_project(self, **kwargs):
        project = FakeProject(**kwargs)
        self.projects.append(project)
        return project

    def find_project_by_git_remote(self, repo_remote: str):
        return next((project for project in self.projects if repo_remote in project.git_remotes), None)

    def create_session(self, **kwargs):
        session = FakeSession(**kwargs)
        self.sessions.append(session)
        return session

    def get_session(self, session_id: str):
        return next((session for session in self.sessions if session.id == session_id), None)

    def record_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class FakeContextEngine:
    def plan_context(self, *, org_id: str, project_id: str, intent: str, query: str, token_budget: int = 4000):
        return PlannedContextPack(
            id="ctx_1",
            org_id=org_id,
            project_id=project_id,
            level="L1",
            intent=intent,
            summary=f"Context for {query}",
            source_refs=[{"asset_id": "asset_1"}],
        )


@pytest.fixture
def fake_core():
    return FakeCore()


@pytest.fixture
def fake_context_engine():
    return FakeContextEngine()
