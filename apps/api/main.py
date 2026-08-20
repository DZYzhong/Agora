from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from apps.api.routers.harness import router as harness_router
from apps.api.routers.health import router as health_router
from apps.api.routers.projects import router as projects_router
from apps.api.routers.assets import router as assets_router
from apps.api.routers.sessions import router as sessions_router
from apps.api.routers.skills import router as skills_router
from apps.api.routers.writebacks import router as writebacks_router
from apps.api.auth import bootstrap_auth_from_env
from apps.api.dependencies import get_engine
from packages.core.services.runtime import CoreRuntime
from packages.core.services.skills import ensure_builtin_skills_for_existing_projects
from packages.core.uow import SqlAlchemyUnitOfWork


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
    bootstrap_auth_from_env()
    _bootstrap_builtin_skills()
    yield


app = FastAPI(title="Agora API", lifespan=lifespan)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(assets_router)
app.include_router(harness_router)
app.include_router(sessions_router)
app.include_router(skills_router)
app.include_router(writebacks_router)
