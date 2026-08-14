import ast
import inspect
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_db_session, get_engine
from apps.api.main import app
from packages.core.models import ContextPackModel, SessionEventModel, TaskSessionModel, WritebackModel
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository
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
