from dataclasses import dataclass, field
from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def isolate_agora_api_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("AGORA_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'agora-test.db'}")

    from apps.api import dependencies

    dependencies.get_engine.cache_clear()
    dependencies.get_keyword_index.cache_clear()
    dependencies.get_vector_index.cache_clear()
    yield
    dependencies.get_engine.cache_clear()
    dependencies.get_keyword_index.cache_clear()
    dependencies.get_vector_index.cache_clear()


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
    content_hash: str | None = None
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


class SharedFakeCore:
    def __init__(self):
        self.assets: list[FakeAsset] = []
        self.writebacks: list[FakeWriteback] = []

    def create_asset(self, **kwargs):
        asset = FakeAsset(**kwargs)
        self.assets.append(asset)
        return asset

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


@pytest.fixture
def fake_core():
    return SharedFakeCore()
