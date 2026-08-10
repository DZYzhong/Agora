from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])
