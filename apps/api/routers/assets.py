from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.repositories.assets import AssetRepository

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


def _serialize_asset(asset, *, with_content: bool = False) -> dict:
    data = {
        "id": asset.id,
        "project_id": asset.project_id,
        "type": asset.type,
        "source": asset.source,
        "source_uri": asset.source_uri,
        "title": asset.title,
        "summary": asset.summary,
        "content_hash": asset.content_hash,
        "created_at": asset.created_at,
    }
    if with_content:
        data["content"] = asset.content
    return data


@router.get("")
def list_assets(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    assets = AssetRepository(session).list_by_project(project_id)
    return [_serialize_asset(asset) for asset in assets]


@router.get("/{asset_id}")
def get_asset(
    project_id: str,
    asset_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    asset = AssetRepository(session).get(asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _serialize_asset(asset, with_content=True)
