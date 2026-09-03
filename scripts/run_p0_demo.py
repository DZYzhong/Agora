"""
NOTE: dev/test seeding helper ONLY — not part of the product API or UI.
"""
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
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


class DemoCore:
    def __init__(self):
        self.projects: list[Project] = []
        self.sessions: list[Session] = []
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

    def get_session(self, session_id: str):
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


def main() -> None:
    core = DemoCore()
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
    print(f"project initialized: {project.name}, assets={init.asset_count}")

    context_engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    harness = HarnessService(core=core, context_engine=context_engine)
    started = harness.start_work(
        user_message="分析如何实现退款失败重试",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
    )
    context = harness.plan_context(session_id=started.session_id, query="退款失败重试", token_budget=1000)
    print(f"context summary: {context.summary}")

    print("skill output: impact-analysis would inspect refund retry risks")

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
    print(f"writeback accepted: {accepted.writeback.title}")

    later = context_engine.plan_context(
        org_id="org_1",
        project_id=project.id,
        intent="implementation",
        query="退款失败重试 幂等",
        token_budget=1000,
    )
    print(f"later retrieval summary: {later.summary}")


if __name__ == "__main__":
    main()
