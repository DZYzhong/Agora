from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.writebacks import WritebackService

router = APIRouter(prefix="/projects/{project_id}/writebacks", tags=["writebacks"])


@router.get("")
def list_writebacks(project_id: str, session: Session = Depends(get_db_session)):
    writebacks = WritebackService(session).list_by_project(project_id)
    return [
        {
            "id": writeback.id,
            "project_id": writeback.project_id,
            "type": writeback.type,
            "title": writeback.title,
            "content": writeback.content,
            "status": writeback.status,
        }
        for writeback in writebacks
    ]


@router.post("/{writeback_id}/accept")
def accept_writeback(project_id: str, writeback_id: str, session: Session = Depends(get_db_session)):
    try:
        writeback = WritebackService(session).accept(writeback_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": writeback.id, "project_id": project_id, "status": writeback.status, "accepted_asset_id": writeback.accepted_asset_id}


@router.post("/{writeback_id}/reject")
def reject_writeback(project_id: str, writeback_id: str, session: Session = Depends(get_db_session)):
    try:
        writeback = WritebackService(session).reject(writeback_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": writeback.id, "project_id": project_id, "status": writeback.status}
