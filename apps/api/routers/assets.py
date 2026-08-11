from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.repositories.assets import AssetRepository

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


@router.get("")
def list_assets(project_id: str, session: Session = Depends(get_db_session)):
    assets = AssetRepository(session).list_by_project(project_id)
    return [
        {
            "id": asset.id,
            "project_id": asset.project_id,
            "type": asset.type,
            "source": asset.source,
            "source_uri": asset.source_uri,
            "title": asset.title,
            "summary": asset.summary,
        }
        for asset in assets
    ]
