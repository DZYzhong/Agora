from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import (
    create_readiness_probe_engine,
    get_engine,
    get_runtime_policy,
)
from packages.core.models import ContextProposalModel, ProjectModel
from packages.core.schema_manager import get_alembic_heads
from packages.core.services.outbox_diagnostics import build_outbox_summary
from packages.core.settings import RuntimeConfigurationError

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def build_readiness_result() -> dict[str, Any]:
    checks: dict[str, dict[str, str]] = {
        "configuration": {"status": "unknown", "code": "CHECK_NOT_RUN"},
        "database": {"status": "unknown", "code": "CHECK_NOT_RUN"},
        "schema": {"status": "unknown", "code": "CHECK_NOT_RUN"},
    }

    try:
        runtime_policy = get_runtime_policy()
    except RuntimeConfigurationError as exc:
        checks["configuration"] = {
            "status": "error",
            "code": exc.code,
            "error": type(exc).__name__,
        }
        return {"status": "not_ready", "checks": checks}
    except Exception as exc:
        checks["configuration"] = {
            "status": "error",
            "code": "RUNTIME_POLICY_LOAD_FAILED",
            "error": type(exc).__name__,
        }
        return {"status": "not_ready", "checks": checks}
    checks["configuration"] = {"status": "ok", "code": "RUNTIME_POLICY_VALID"}

    try:
        engine = create_readiness_probe_engine(runtime_policy)
    except Exception as exc:
        checks["database"] = {
            "status": "error",
            "code": "ENGINE_CREATION_FAILED",
            "error": type(exc).__name__,
        }
        return {"status": "not_ready", "checks": checks}

    try:
        try:
            connection_context = engine.connect()
            with connection_context as connection:
                try:
                    connection.execute(text("SELECT 1"))
                except Exception as exc:
                    checks["database"] = {
                        "status": "error",
                        "code": "DATABASE_QUERY_FAILED",
                        "error": type(exc).__name__,
                    }
                    return {"status": "not_ready", "checks": checks}
                checks["database"] = {"status": "ok", "code": "DATABASE_REACHABLE"}

                try:
                    has_revision_table = inspect(connection).has_table("alembic_version")
                    revisions = (
                        connection.scalars(
                            text("SELECT version_num FROM alembic_version")
                        ).all()
                        if has_revision_table
                        else []
                    )
                except Exception as exc:
                    checks["schema"] = {
                        "status": "error",
                        "code": "SCHEMA_QUERY_FAILED",
                        "error": type(exc).__name__,
                    }
                    return {"status": "not_ready", "checks": checks}
        except Exception as exc:
            checks["database"] = {
                "status": "error",
                "code": "DATABASE_CONNECTION_FAILED",
                "error": type(exc).__name__,
            }
            return {"status": "not_ready", "checks": checks}
    finally:
        engine.dispose()

    if not revisions:
        checks["schema"] = {"status": "error", "code": "SCHEMA_REVISION_MISSING"}
        return {"status": "not_ready", "checks": checks}

    try:
        expected_revisions = get_alembic_heads()
    except Exception as exc:
        checks["schema"] = {
            "status": "error",
            "code": "SCHEMA_HEAD_LOOKUP_FAILED",
            "error": type(exc).__name__,
        }
        return {"status": "not_ready", "checks": checks}

    if not expected_revisions:
        checks["schema"] = {"status": "error", "code": "SCHEMA_HEAD_MISSING"}
        return {"status": "not_ready", "checks": checks}
    if len(revisions) != len(set(revisions)) or set(revisions) != set(
        expected_revisions
    ):
        checks["schema"] = {"status": "error", "code": "SCHEMA_REVISION_STALE"}
        return {"status": "not_ready", "checks": checks}

    checks["schema"] = {"status": "ok", "code": "SCHEMA_CURRENT"}
    return {"status": "ready", "checks": checks}


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    result = build_readiness_result()
    response.status_code = (
        status.HTTP_200_OK
        if result["status"] == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return result


@router.get("/metrics")
def metrics() -> Response:
    readiness = build_readiness_result()
    ready_value = 1 if readiness["status"] == "ready" else 0
    project_count = 0
    pending_context_count = 0
    outbox = {"by_status": {}, "retryable": 0}

    if ready_value:
        try:
            engine = get_engine()
            with sessionmaker(bind=engine)() as session:
                project_count = session.scalar(func.count(ProjectModel.id)) or 0
                pending_context_count = (
                    session.query(ContextProposalModel)
                    .filter(ContextProposalModel.status.in_(["submitted", "needs_rebase"]))
                    .count()
                )
                outbox = build_outbox_summary(session, max_attempts=3, dead_limit=1)
        except Exception:
            ready_value = 0
            project_count = 0
            pending_context_count = 0
            outbox = {"by_status": {}, "retryable": 0}

    schema_code = readiness["checks"]["schema"]["code"]
    lines = [
        "# TYPE agora_ready gauge",
        f"agora_ready {ready_value}",
        "# TYPE agora_schema_revision_info gauge",
        f'agora_schema_revision_info{{status="{schema_code}"}} 1',
        "# TYPE agora_projects_total gauge",
        f"agora_projects_total {project_count}",
        "# TYPE agora_pending_context_proposals_total gauge",
        f"agora_pending_context_proposals_total {pending_context_count}",
        "# TYPE agora_outbox_events_total gauge",
    ]
    for event_status, count in outbox["by_status"].items():
        lines.append(f'agora_outbox_events_total{{status="{event_status}"}} {count}')
    lines.extend(
        [
            "# TYPE agora_outbox_retryable_total gauge",
            f"agora_outbox_retryable_total {outbox['retryable']}",
            "",
        ]
    )
    return Response(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4",
    )
