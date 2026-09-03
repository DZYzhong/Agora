from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import sessionmaker

from apps.api.middleware import (
    BodyLimitMiddleware,
    CsrfProtectionMiddleware,
    HideProductionLocalInitializationMiddleware,
    RequestIdMiddleware,
)
from apps.api.routers.harness import router as harness_router
from apps.api.routers.health import router as health_router
from apps.api.routers.auth import router as auth_router
from apps.api.routers.context_governance import router as context_governance_router
from apps.api.routers.integrations import router as integrations_router
from apps.api.routers.projects import router as projects_router
from apps.api.routers.assets import router as assets_router
from apps.api.routers.sessions import router as sessions_router
from apps.api.routers.skills import router as skills_router
from apps.api.routers.work_items import router as work_items_router
from apps.api.routers.writebacks import router as writebacks_router
from apps.api.routers.users import router as users_router
from apps.api.routers.approvals import router as approvals_router
from apps.api.routers.memberships import router as memberships_router
from apps.api.auth import bootstrap_auth_from_env
from apps.api.dependencies import get_engine, get_runtime_policy
from packages.core.services.runtime import CoreRuntime
from packages.core.services.skills import ensure_builtin_skills_for_existing_projects
from packages.core.uow import SqlAlchemyUnitOfWork

DEFAULT_DEV_WEB_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://127.0.0.1:13100",
    "http://127.0.0.1:13120",
    "http://127.0.0.1:13140",
    "http://localhost:3000",
)


def _configure_cors(app: FastAPI) -> None:
    """CORS allow-list from AGORA_ALLOWED_ORIGINS plus the localhost dev origins.

    No wildcard is ever allowed alongside credentials.
    """
    import os

    from starlette.middleware.cors import CORSMiddleware

    configured = os.environ.get("AGORA_ALLOWED_ORIGINS", "")
    origins = [item.strip() for item in configured.split(",") if item.strip()]
    origins.extend(DEFAULT_DEV_WEB_ORIGINS)
    origins = list(dict.fromkeys(origins))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["content-type", "authorization", "x-csrf-token", "idempotency-key", "agora-protocol-version", "agora-connector-version", "x-request-id"],
    )


def _bootstrap_builtin_skills() -> None:
    session = sessionmaker(bind=get_engine())()
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            ensure_builtin_skills_for_existing_projects(CoreRuntime(session))
            uow.commit()
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime_policy = get_runtime_policy()
    bootstrap_auth_from_env(runtime_policy)
    _bootstrap_builtin_skills()
    yield


app = FastAPI(title="Agora API", lifespan=lifespan)
app.add_middleware(HideProductionLocalInitializationMiddleware)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(CsrfProtectionMiddleware)
app.add_middleware(RequestIdMiddleware)

_configure_cors(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(assets_router)
app.include_router(harness_router)
app.include_router(sessions_router)
app.include_router(skills_router)
app.include_router(context_governance_router)
app.include_router(integrations_router)
app.include_router(work_items_router)
app.include_router(writebacks_router)
app.include_router(users_router)
app.include_router(approvals_router)
app.include_router(memberships_router)


def custom_openapi():
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    if get_runtime_policy().environment == "production":
        schema["paths"].pop("/projects/{project_id}/initialize-local", None)
        schema["paths"].pop(
            "/projects/{project_id}/initialization-jobs/{job_id}/retry",
            None,
        )
    return schema


app.openapi = custom_openapi
