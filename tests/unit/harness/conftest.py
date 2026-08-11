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


@dataclass
class FakeSkill:
    slug: str
    status: str
    id: str = field(default_factory=lambda: uuid4().hex)
    org_id: str | None = None
    project_id: str | None = None
    name: str | None = None
    definition: dict = field(default_factory=dict)


@dataclass
class FakeSkillRun:
    org_id: str
    project_id: str
    skill_id: str
    input: dict
    output: dict
    session_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    status: str = "completed"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class FakeWriteback:
    org_id: str
    project_id: str
    type: str
    title: str
    content: str
    session_id: str | None = None
    asset_refs: list[str] = field(default_factory=list)
    status: str = "draft"
    id: str = field(default_factory=lambda: uuid4().hex)
    accepted_asset_id: str | None = None


@dataclass
class FakeAsset:
    org_id: str
    project_id: str
    type: str
    source: str
    source_uri: str
    title: str
    content: str
    summary: str | None = None
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)


class FakeCore:
    def __init__(self):
        self.projects: list[FakeProject] = []
        self.sessions: list[FakeSession] = []
        self.events: list[dict] = []
        self.skills: list[FakeSkill] = []
        self.skill_runs: list[FakeSkillRun] = []
        self.writebacks: list[FakeWriteback] = []
        self.assets: list[FakeAsset] = []

    def create_project(self, **kwargs):
        project = FakeProject(**kwargs)
        self.projects.append(project)
        return project

    def find_project_by_git_remote(self, repo_remote: str):
        return next((project for project in self.projects if repo_remote in project.git_remotes), None)

    def get_project(self, project_id: str):
        return next((project for project in self.projects if project.id == project_id), None)

    def list_projects(self):
        return self.projects

    def create_session(self, **kwargs):
        session = FakeSession(**kwargs)
        self.sessions.append(session)
        return session

    def get_session(self, session_id: str):
        return next((session for session in self.sessions if session.id == session_id), None)

    def record_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs

    def create_skill(self, **kwargs):
        skill = FakeSkill(**kwargs)
        self.skills.append(skill)
        return skill

    def get_skill_by_slug(self, skill_slug: str):
        return next((skill for skill in self.skills if skill.slug == skill_slug), None)

    def create_skill_run(self, **kwargs):
        run = FakeSkillRun(**kwargs)
        self.skill_runs.append(run)
        return run

    def create_writeback(self, **kwargs):
        writeback = FakeWriteback(**kwargs)
        self.writebacks.append(writeback)
        return writeback

    def get_writeback(self, writeback_id: str):
        return next((writeback for writeback in self.writebacks if writeback.id == writeback_id), None)

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None):
        writeback = self.get_writeback(writeback_id)
        writeback.status = "accepted"
        writeback.accepted_asset_id = accepted_asset_id
        return writeback

    def create_asset(self, **kwargs):
        asset = FakeAsset(**kwargs)
        self.assets.append(asset)
        return asset


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
