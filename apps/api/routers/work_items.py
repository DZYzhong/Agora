from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.runtime import CoreRuntime

router = APIRouter(prefix="/projects/{project_id}/work-items", tags=["work-items"])


@router.get("")
def list_work_items(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    runtime = CoreRuntime(session)
    return [
        {
            "id": work_item.id,
            "project_id": work_item.project_id,
            "external_key": work_item.external_key,
            "title": work_item.title,
            "status": work_item.status,
            "stage": work_item.stage,
            "source": work_item.source,
            "session_count": session_count,
        }
        for work_item, session_count in runtime.list_work_items_by_project(project_id)
    ]
