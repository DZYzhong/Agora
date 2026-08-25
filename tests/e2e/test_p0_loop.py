from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
from packages.core.auth import Principal
from packages.harness.memory_writeback import MemoryWritebackService
from packages.harness.service import HarnessService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


@dataclass
class Project:
    org_id: str
    name: str
    slug: str
    git_remotes: list[str]
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class Session:
    org_id: str
    project_id: str
    agent_type: str
    intent: str
    task_id: str | None = None
    status: str = "started"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class WorkItem:
    org_id: str
    project_id: str
    title: str
    external_key: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class WorkSession:
    work_item_id: str
    user_id: str
    credential_id: str
    agent_type: str
    intent: str
    initial_request_id: str | None = None
    workflow_version_id: str | None = None
    workflow_execution_id: str | None = None
    status: str = "started"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class Asset:
    org_id: str
    project_id: str
    type: str
    source: str
    source_uri: str
    title: str
    content: str
    summary: str | None = None
    metadata: dict = field(default_factory=dict)
    content_hash: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class Writeback:
    org_id: str
    project_id: str
    type: str
    title: str
    content: str
    session_id: str | None = None
    asset_refs: list[str] = field(default_factory=list)
    status: str = "draft"
    accepted_asset_id: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


class E2eCore:
    def __init__(self):
        self.projects: list[Project] = []
        self.sessions: list[Session] = []
        self.work_items: list[WorkItem] = []
        self.work_sessions: list[WorkSession] = []
        self.assets: list[Asset] = []
        self.writebacks: list[Writeback] = []
        self.events: list[dict] = []

    def create_project(self, **kwargs):
        project = Project(**kwargs)
        self.projects.append(project)
        return project

    def find_project_by_git_remote(self, repo_remote: str):
        return next((project for project in reversed(self.projects) if repo_remote in project.git_remotes), None)

    def create_session(self, **kwargs):
        session = Session(**kwargs)
        self.sessions.append(session)
        return session

    def create_work_item(self, **kwargs):
        work_item = WorkItem(**kwargs)
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
        work_session = WorkSession(**kwargs)
        self.work_sessions.append(work_session)
        work_item = self.get_work_item(work_session.work_item_id)
        return type(
            "WorkSessionView",
            (),
            {
                "id": work_session.id,
                "org_id": work_item.org_id,
                "project_id": work_item.project_id,
                "task_id": work_item.external_key,
                "agent_type": work_session.agent_type,
                "intent": work_session.intent,
                "status": work_session.status,
                "workflow_version_id": work_session.workflow_version_id,
                "workflow_execution_id": work_session.workflow_execution_id,
            },
        )()

    def get_session(self, session_id: str):
        work_session = next((session for session in self.work_sessions if session.id == session_id), None)
        if work_session is not None:
            work_item = self.get_work_item(work_session.work_item_id)
            return type(
                "WorkSessionView",
                (),
                {
                    "id": work_session.id,
                    "org_id": work_item.org_id,
                    "project_id": work_item.project_id,
                    "task_id": work_item.external_key,
                    "agent_type": work_session.agent_type,
                    "intent": work_session.intent,
                    "status": work_session.status,
                    "workflow_version_id": work_session.workflow_version_id,
                    "workflow_execution_id": work_session.workflow_execution_id,
                },
            )()
        return next((session for session in self.sessions if session.id == session_id), None)

    def record_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs

    def create_asset(self, **kwargs):
        asset = Asset(**kwargs)
        self.assets.append(asset)
        return asset

    def create_writeback(self, **kwargs):
        writeback = Writeback(**kwargs)
        self.writebacks.append(writeback)
        return writeback

    def get_writeback(self, writeback_id: str):
        return next((writeback for writeback in self.writebacks if writeback.id == writeback_id), None)

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None):
        writeback = self.get_writeback(writeback_id)
        writeback.status = "accepted"
        writeback.accepted_asset_id = accepted_asset_id
        return writeback


def test_p0_loop():
    core = E2eCore()
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()

    project = core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    init = initialize_project_from_local_repo(
        org_id="org_1",
        project_id=project.id,
        repo_path=Path("tests/fixtures/sample_repo"),
    )
    for asset in init.assets:
        stored = core.create_asset(**asset.model_dump())
        keyword.index_asset(stored.id, asset)
        vector.index_asset(stored.id, asset)

    context_engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    harness = HarnessService(core=core, context_engine=context_engine)

    started = harness.start_work(
        user_message="分析如何实现退款失败重试",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
        principal=Principal(
            org_id="org_1",
            user_id="user_1",
            credential_id="credential_1",
            credential_kind="agent",
            token_prefix="test",
        ),
    )
    context = harness.plan_context(session_id=started.session_id, query="退款失败重试", token_budget=1000)

    assert context.summary
    assert context.source_refs

    writeback_service = MemoryWritebackService(core=core)
    writeback = writeback_service.prepare_writeback(
        org_id="org_1",
        project_id=project.id,
        session_id=started.session_id,
        type="development_summary",
        title="退款失败重试总结",
        content="退款失败重试需要限制次数并保持幂等。",
    )
    accepted = writeback_service.accept_writeback(writeback.id)
    keyword.index_asset(accepted.pending_index.asset_id, accepted.pending_index.asset)
    vector.index_asset(accepted.pending_index.asset_id, accepted.pending_index.asset)

    later = context_engine.plan_context(
        org_id="org_1",
        project_id=project.id,
        intent="implementation",
        query="退款失败重试 幂等",
        token_budget=1000,
    )
    assert "幂等" in later.summary
