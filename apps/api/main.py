from fastapi import FastAPI

from apps.api.routers.health import router as health_router

app = FastAPI(title="Agora API")
app.include_router(health_router)
