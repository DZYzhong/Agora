from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def isolate_agora_api_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("AGORA_ENV", "test")
    monkeypatch.setenv("AGORA_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'agora-test.db'}")
    monkeypatch.setenv("AGORA_TEST_AUTH_BYPASS", "1")

    from apps.api import dependencies
    from apps.api.auth_session import rate_limiter

    dependencies.get_engine.cache_clear()
    dependencies.get_keyword_index.cache_clear()
    dependencies.get_vector_index.cache_clear()
    rate_limiter.reset()
    yield
    dependencies.get_engine.cache_clear()
    dependencies.get_keyword_index.cache_clear()
    dependencies.get_vector_index.cache_clear()


@pytest.fixture
def local_init_root(monkeypatch, tmp_path) -> Path:
    root = tmp_path / "local-init"
    root.mkdir()
    monkeypatch.setenv("AGORA_ENV", "test")
    monkeypatch.setenv("AGORA_LOCAL_INIT_ROOT", str(root))
    return root


class AuthenticatedTestClient:
    def __init__(self, client, token: str):
        self._client = client
        self._token = token

    def __getattr__(self, name):
        return getattr(self._client, name)

    def get(self, url, *args, headers=None, **kwargs):
        return self._client.get(url, *args, headers=self._headers(headers), **kwargs)

    def post(self, url, *args, headers=None, **kwargs):
        return self._client.post(url, *args, headers=self._headers(headers), **kwargs)

    def put(self, url, *args, headers=None, **kwargs):
        return self._client.put(url, *args, headers=self._headers(headers), **kwargs)

    def delete(self, url, *args, headers=None, **kwargs):
        return self._client.delete(url, *args, headers=self._headers(headers), **kwargs)

    def _headers(self, headers):
        merged = {"Authorization": f"Bearer {self._token}"}
        if headers:
            merged.update(headers)
        return merged


@pytest.fixture
def authenticated_client(monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    token = "test-human-token-secret-value"
    monkeypatch.setenv("AGORA_ENV", "test")
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", token)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", "test-agent-token-secret-value")
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", "test-ci-token-secret-value")
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "test-org")
    with TestClient(app) as client:
        yield AuthenticatedTestClient(client, token)


@pytest.fixture
def authenticated_client_no_raise(monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    token = "test-human-token-secret-value"
    monkeypatch.setenv("AGORA_ENV", "test")
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", token)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", "test-agent-token-secret-value")
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", "test-ci-token-secret-value")
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "test-org")
    with TestClient(app, raise_server_exceptions=False) as client:
        yield AuthenticatedTestClient(client, token)


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
