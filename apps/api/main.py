from fastapi import FastAPI

from apps.api.routers.harness import router as harness_router
from apps.api.routers.health import router as health_router
from apps.api.routers.projects import router as projects_router

app = FastAPI(title="Agora API")
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(harness_router)
