import ast
import inspect
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_db_session, get_engine, get_keyword_index, get_vector_index
from apps.api.main import app
from packages.core.models import (
    AssetModel,
    ContextPackModel,
    SessionEventModel,
    SkillRunModel,
    TaskSessionModel,
    WritebackModel,
)
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.repositories.writebacks import WritebackRepository
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork


PROJECT_ROOT = Path(__file__).parents[3]
READ_ONLY_POST_PATHS = {"/harness/fetch-context-ref"}
MUTATION_METHODS = {
    "accept",
    "accept_writeback",
    "archive",
    "create",
    "create_asset",
    "create_context_pack",
    "create_session",
    "create_skill",
    "create_skill_run",
    "create_writeback",
    "mark_completed",
    "mark_failed",
    "prune_project_sources",
    "record_event",
    "reject",
    "start_work",
    "update_skill",
    "upsert_by_source_uri",
}


def _api_routes():
    for route in app.routes:
        if hasattr(route, "original_router"):
            yield from route.original_router.routes
        elif hasattr(route, "methods"):
            yield route


def _persist_session() -> tuple[str, str]:
    session = sessionmaker(bind=get_engine())()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(
            org_id="org_tx",
            name="Transaction Boundaries",
            slug="transaction-boundaries",
        )
        task_session = TaskSessionRepository(session).create(
            org_id=project.org_id,
            project_id=project.id,
            agent_type="codex",
            intent="implementation",
        )
        project_id = project.id
        session_id = task_session.id
        uow.commit()
    session.close()
    return project_id, session_id


def _start_api_session(client: TestClient, *, suffix: str) -> tuple[dict, str]:
    project = client.post(
        "/projects",
        json={
            "org_id": f"org_{suffix}",
            "name": f"Writeback {suffix}",
            "slug": f"writeback-{suffix}",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "Capture atomic writeback",
            "agent_type": "codex",
        },
    ).json()
    return project, started["session_id"]


def _prepare_api_writeback(client: TestClient, *, session_id: str, type: str, title: str) -> dict:
    return client.post(
        "/harness/prepare-writeback",
        json={
            "session_id": session_id,
            "type": type,
            "title": title,
            "content": f"{title} must be indexed only after commit.",
            "asset_refs": [],
        },
    ).json()


def test_successful_http_mutation_command_is_committed():
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={
            "org_id": "org_success",
            "name": "Successful Command",
            "slug": "successful-command",
            "git_remotes": [],
        },
    )

    assert response.status_code == 201
    assert client.get(f"/projects/{response.json()['id']}").status_code == 200


def test_request_session_dependency_owns_lifetime_not_transactions():
    source = inspect.getsource(get_db_session)

    assert ".commit(" not in source
    assert ".rollback(" not in source
    assert "SqlAlchemyUnitOfWork" not in source


def test_failed_plan_context_rolls_back_flushed_context_pack_and_event(monkeypatch):
    project_id, session_id = _persist_session()

    def fail_record_event(self, **kwargs):
        raise RuntimeError("event persistence failed")

    monkeypatch.setattr(CoreRuntime, "record_event", fail_record_event)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/harness/plan-context",
        json={"session_id": session_id, "query": "atomic command", "token_budget": 1000},
    )

    assert response.status_code == 500
    with sessionmaker(bind=get_engine())() as session:
        assert session.scalar(select(func.count()).select_from(ContextPackModel)) == 0
        assert session.scalar(select(func.count()).select_from(SessionEventModel)) == 0
        assert session.get(TaskSessionModel, session_id).project_id == project_id


def test_failed_close_work_rolls_back_session_writeback_and_event(monkeypatch):
    _, session_id = _persist_session()

    def fail_record_event(self, **kwargs):
        raise RuntimeError("event persistence failed")

    monkeypatch.setattr(CoreRuntime, "record_event", fail_record_event)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/harness/close-work",
        json={
            "session_id": session_id,
            "status": "closed",
            "agent_summary": "This write must roll back with the command.",
        },
    )

    assert response.status_code == 500
    with sessionmaker(bind=get_engine())() as session:
        task_session = session.get(TaskSessionModel, session_id)
        assert task_session.status == "started"
        assert task_session.closed_at is None
        assert session.scalar(select(func.count()).select_from(WritebackModel)) == 0
        assert session.scalar(select(func.count()).select_from(SessionEventModel)) == 0


def test_failed_writeback_accept_rolls_back_asset_without_index_pollution(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project, session_id = _start_api_session(client, suffix="accept_failure")
    writeback = _prepare_api_writeback(
        client,
        session_id=session_id,
        type="development_summary",
        title="Accept failure",
    )

    def fail_accept(self, writeback_id, *, accepted_asset_id=None):
        raise RuntimeError("injected writeback accept failure")

    monkeypatch.setattr(WritebackRepository, "accept", fail_accept)

    response = client.post(f"/projects/{project['id']}/writebacks/{writeback['id']}/accept")

    assert response.status_code == 500
    with sessionmaker(bind=get_engine())() as session:
        stored = session.get(WritebackModel, writeback["id"])
        assert stored.status == "draft"
        assert stored.accepted_asset_id is None
        assert session.scalar(select(func.count()).select_from(AssetModel)) == 0
    assert get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"]) == []
    assert get_vector_index()._assets == []


def test_failed_candidate_skill_write_rolls_back_new_asset_and_indexes(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project, session_id = _start_api_session(client, suffix="skill_failure")
    first = _prepare_api_writeback(
        client,
        session_id=session_id,
        type="release_risk_review",
        title="First accepted review",
    )
    first_response = client.post(f"/projects/{project['id']}/writebacks/{first['id']}/accept")
    assert first_response.status_code == 200
    second = _prepare_api_writeback(
        client,
        session_id=session_id,
        type="release_risk_review",
        title="Second rejected review",
    )
    asset_ids_before = {asset["id"] for asset in client.get(f"/projects/{project['id']}/assets").json()}
    keyword_ids_before = {
        item.asset_id
        for item in get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"])
    }
    vector_ids_before = {asset_id for asset_id, _ in get_vector_index()._assets}

    def fail_candidate_skill(self, **kwargs):
        raise RuntimeError("injected candidate skill failure")

    monkeypatch.setattr(SkillRepository, "create", fail_candidate_skill)

    response = client.post(f"/projects/{project['id']}/writebacks/{second['id']}/accept")

    assert response.status_code == 500
    assert {asset["id"] for asset in client.get(f"/projects/{project['id']}/assets").json()} == asset_ids_before
    writebacks = client.get(f"/projects/{project['id']}/writebacks").json()
    stored_second = next(item for item in writebacks if item["id"] == second["id"])
    assert stored_second["status"] == "draft"
    assert stored_second["accepted_asset_id"] is None
    keyword_ids_after = {
        item.asset_id
        for item in get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"])
    }
    vector_ids_after = {asset_id for asset_id, _ in get_vector_index()._assets}
    assert keyword_ids_after == keyword_ids_before
    assert vector_ids_after == vector_ids_before
    skills = client.get(f"/projects/{project['id']}/skills").json()
    assert not any(skill["slug"] == "release-risk-review" for skill in skills)


def test_successful_writeback_accept_indexes_only_after_database_commit(monkeypatch):
    client = TestClient(app)
    project, session_id = _start_api_session(client, suffix="accept_success")
    writeback = _prepare_api_writeback(
        client,
        session_id=session_id,
        type="development_summary",
        title="Committed accept",
    )
    keyword_index = get_keyword_index()
    original_index_asset = keyword_index.index_asset
    observations = []

    def observe_committed_state(asset_id, asset):
        with sessionmaker(bind=get_engine())() as session:
            stored_asset = session.get(AssetModel, asset_id)
            stored_writeback = session.get(WritebackModel, writeback["id"])
            observations.append(
                (
                    stored_asset is not None,
                    stored_writeback.status,
                    stored_writeback.accepted_asset_id,
                    asset_id,
                )
            )
        original_index_asset(asset_id, asset)

    monkeypatch.setattr(keyword_index, "index_asset", observe_committed_state)

    response = client.post(f"/projects/{project['id']}/writebacks/{writeback['id']}/accept")

    assert response.status_code == 200
    accepted_asset_id = response.json()["accepted_asset_id"]
    assert observations == [(True, "accepted", accepted_asset_id, accepted_asset_id)]
    assert {asset_id for asset_id, _ in get_vector_index()._assets} == {accepted_asset_id}


def test_writeback_accept_index_failure_returns_committed_response_and_retry_is_idempotent(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    project, session_id = _start_api_session(client, suffix="accept_index_failure")
    writeback = _prepare_api_writeback(
        client,
        session_id=session_id,
        type="development_summary",
        title="Committed despite index failure",
    )
    keyword_index = get_keyword_index()
    calls = 0

    def fail_first_keyword_index(asset_id, asset):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("keyword index unavailable")

    monkeypatch.setattr(keyword_index, "index_asset", fail_first_keyword_index)

    first = client.post(f"/projects/{project['id']}/writebacks/{writeback['id']}/accept")

    assert first.status_code == 200
    first_body = first.json()
    assert first_body["status"] == "accepted"
    assert first_body["accepted_asset_id"]
    assert first_body["index_status"] == "pending_rebuild"
    assert any("keyword index unavailable" in warning for warning in first_body["warnings"])
    with sessionmaker(bind=get_engine())() as session:
        assert session.scalar(select(func.count()).select_from(AssetModel)) == 1
        stored = session.get(WritebackModel, writeback["id"])
        assert stored.status == "accepted"
        assert stored.accepted_asset_id == first_body["accepted_asset_id"]

    second = client.post(f"/projects/{project['id']}/writebacks/{writeback['id']}/accept")

    assert second.status_code == 200
    assert second.json()["accepted_asset_id"] == first_body["accepted_asset_id"]
    with sessionmaker(bind=get_engine())() as session:
        assert session.scalar(select(func.count()).select_from(AssetModel)) == 1


def test_failed_skill_execution_rolls_back_partial_run_before_failed_audit(monkeypatch):
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_run_failure",
            "name": "Skill Run Failure",
            "slug": "skill-run-failure",
            "git_remotes": [],
        },
    ).json()
    skill = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "atomic-skill-run",
            "name": "Atomic Skill Run",
            "status": "approved",
            "definition": {"instructions": "Run atomically."},
        },
    ).json()
    original_create_run = SkillRepository.create_run
    create_attempts = 0
    run_counts_before_audit = []

    def create_then_fail_once(self, **kwargs):
        nonlocal create_attempts
        create_attempts += 1
        if create_attempts == 2:
            run_counts_before_audit.append(self.session.scalar(select(func.count()).select_from(SkillRunModel)))
        run = original_create_run(self, **kwargs)
        if create_attempts == 1:
            raise ValueError("execution failed after run flush")
        return run

    monkeypatch.setattr(SkillRepository, "create_run", create_then_fail_once)

    response = client.post(
        f"/projects/{project['id']}/skills/{skill['id']}/run",
        json={"input": {"change": "atomic"}, "context": {"summary": "Atomic skill execution."}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "execution failed after run flush"
    assert run_counts_before_audit == [0]
    with sessionmaker(bind=get_engine())() as session:
        runs = list(session.scalars(select(SkillRunModel)).all())
        assert len(runs) == 1
        assert runs[0].skill_id == skill["id"]
        assert runs[0].status == "failed"
        assert runs[0].output == {"error": "execution failed after run flush"}
        assert runs[0].warnings == ["execution failed after run flush"]


def test_http_mutation_routes_own_an_explicit_unit_of_work():
    offenders = []
    for route in _api_routes():
        methods = route.methods or set()
        if not methods.intersection({"POST", "PUT", "PATCH", "DELETE"}):
            continue
        if route.path in READ_ONLY_POST_PATHS:
            continue
        source = inspect.getsource(route.endpoint)
        if "SqlAlchemyUnitOfWork" not in source or "uow.commit()" not in source:
            offenders.append(f"{sorted(methods)} {route.path}")

    assert offenders == [], f"Mutation routes without an explicit committing UoW: {offenders}"


def test_read_only_http_endpoints_do_not_create_a_unit_of_work():
    offenders = []
    for route in _api_routes():
        methods = route.methods or set()
        if methods == {"GET"} or route.path in READ_ONLY_POST_PATHS:
            source = inspect.getsource(route.endpoint)
            assert "SqlAlchemyUnitOfWork" not in source
            tree = ast.parse(source)
            for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
                if isinstance(call.func, ast.Attribute) and call.func.attr in MUTATION_METHODS:
                    offenders.append(f"{sorted(methods)} {route.path}:{call.lineno}")
                if isinstance(call.func, ast.Name) and call.func.id == "_ensure_builtin_skills":
                    offenders.append(f"{sorted(methods)} {route.path}:{call.lineno}")

    assert offenders == [], f"Read-only endpoints calling mutation helpers: {offenders}"


def test_worker_and_admin_repository_mutations_require_a_unit_of_work():
    offenders = []
    for root in (PROJECT_ROOT / "apps/workers", PROJECT_ROOT / "scripts"):
        for path in root.rglob("*.py"):
            if path.name == "run_p0_demo.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                calls = [item for item in ast.walk(node) if isinstance(item, ast.Call)]
                mutates = any(
                    isinstance(call.func, ast.Attribute) and call.func.attr in MUTATION_METHODS
                    for call in calls
                )
                owns_uow = any(
                    isinstance(call.func, ast.Name) and call.func.id == "SqlAlchemyUnitOfWork"
                    for call in calls
                )
                if mutates and not owns_uow:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.name}")

    assert offenders == [], f"Worker/admin mutations without an explicit UoW: {offenders}"
