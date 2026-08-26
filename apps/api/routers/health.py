import os

from fastapi import APIRouter, Response
from sqlalchemy import func, text
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import AGORA_TEST_AUTH_BYPASS, get_engine
from packages.core.models import ContextProposalModel, ProjectModel

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    engine = get_engine()
    checks = {
        "database": {"status": "unknown"},
        "schema": {"status": "unknown", "revision": None},
        "configuration": _configuration_check(),
    }
    status = "ready"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            checks["database"] = {"status": "ok"}
            checks["schema"] = {"status": "ok" if revision else "missing", "revision": revision}
    except Exception as exc:
        status = "not_ready"
        checks["database"] = {"status": "error", "error": type(exc).__name__}
        checks["schema"] = {"status": "unknown", "revision": None}
    if checks["configuration"]["missing_required"]:
        status = "not_ready"
    return {"status": status, "checks": checks}


@router.get("/metrics")
def metrics() -> Response:
    readiness = ready()
    engine = get_engine()
    project_count = 0
    pending_context_count = 0
    with sessionmaker(bind=engine)() as session:
        project_count = session.scalar(func.count(ProjectModel.id)) or 0
        pending_context_count = (
            session.query(ContextProposalModel)
            .filter(ContextProposalModel.status.in_(["submitted", "needs_rebase"]))
            .count()
        )
    revision = readiness["checks"]["schema"]["revision"] or "unknown"
    ready_value = 1 if readiness["status"] == "ready" else 0
    body = "\n".join(
        [
            "# TYPE agora_ready gauge",
            f"agora_ready {ready_value}",
            "# TYPE agora_schema_revision_info gauge",
            f'agora_schema_revision_info{{revision="{revision}"}} 1',
            "# TYPE agora_projects_total gauge",
            f"agora_projects_total {project_count}",
            "# TYPE agora_pending_context_proposals_total gauge",
            f"agora_pending_context_proposals_total {pending_context_count}",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


def _configuration_check() -> dict:
    test_bypass = os.environ.get(AGORA_TEST_AUTH_BYPASS) == "1"
    required = ["AGORA_DATABASE_URL"]
    if not test_bypass:
        required.extend(["AGORA_BOOTSTRAP_HUMAN_TOKEN", "AGORA_BOOTSTRAP_AGENT_TOKEN"])
        if os.environ.get("AGORA_BOOTSTRAP_CI_TOKEN"):
            required.append("AGORA_BOOTSTRAP_CI_TOKEN")
    missing = [name for name in required if not os.environ.get(name)]
    environment = os.environ.get("AGORA_ENV") or ("test" if test_bypass else "local")
    return {
        "status": "ok" if not missing else "missing_required",
        "environment": environment,
        "missing_required": missing,
        "database_url_configured": bool(os.environ.get("AGORA_DATABASE_URL")),
        "ci_token_configured": bool(os.environ.get("AGORA_BOOTSTRAP_CI_TOKEN")),
    }
