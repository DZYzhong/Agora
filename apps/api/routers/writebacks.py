from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/writebacks", tags=["writebacks"])
