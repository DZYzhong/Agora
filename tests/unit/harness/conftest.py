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
class FakeWorkItem:
    org_id: str
    project_id: str
    title: str
    external_key: str | None = None
    description: str | None = None
    owner_id: str | None = None
    source: str = "manual"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class FakeWorkSession:
    work_item_id: str
    user_id: str
    credential_id: str
    agent_type: str
    intent: str
    initial_request_id: str | None = None
    status: str = "started"
    id: str = field(default_factory=lambda: uuid4().hex)
    closed_at: object | None = None


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
        self.work_items: list[FakeWorkItem] = []
        self.work_sessions: list[FakeWorkSession] = []
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

    def create_work_item(self, **kwargs):
        work_item = FakeWorkItem(**kwargs)
        self.work_items.append(work_item)
        return work_item

    def get_work_item(self, work_item_id: str):
        return next((item for item in self.work_items if item.id == work_item_id), None)

    def get_work_item_by_external_key(self, *, project_id: str, external_key: str):
        return next(
            (
                item
                for item in self.work_items
                if item.project_id == project_id and item.external_key == external_key
            ),
            None,
        )

    def find_work_items_by_title(self, *, project_id: str, title: str):
        needle = title.casefold()
        return [
            item
            for item in self.work_items
            if item.project_id == project_id and (needle in item.title.casefold() or item.title.casefold() in needle)
        ]

    def create_work_session(self, **kwargs):
        work_session = FakeWorkSession(**kwargs)
        self.work_sessions.append(work_session)
        return work_session

    def get_session(self, session_id: str):
        work_session = next((session for session in self.work_sessions if session.id == session_id), None)
        if work_session is not None:
            work_item = self.get_work_item(work_session.work_item_id)
            return type(
                "FakeWorkSessionView",
                (),
                {
                    "id": work_session.id,
                    "org_id": work_item.org_id,
                    "project_id": work_item.project_id,
                    "task_id": work_item.external_key,
                    "agent_type": work_session.agent_type,
                    "intent": work_session.intent,
                    "status": work_session.status,
                    "closed_at": work_session.closed_at,
                },
            )()
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
