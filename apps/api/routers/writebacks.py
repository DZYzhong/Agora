from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from packages.core.services.runtime import CoreRuntime
from packages.core.services.writebacks import WritebackService
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.harness.memory_writeback import MemoryWritebackService
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

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
            "accepted_asset_id": writeback.accepted_asset_id,
        }
        for writeback in writebacks
    ]


@router.post("/{writeback_id}/accept")
def accept_writeback(
    project_id: str,
    writeback_id: str,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            service = MemoryWritebackService(core=CoreRuntime(session), keyword_index=keyword_index, vector_index=vector_index)
            writeback = service.accept_writeback(writeback_id)
            response = {
                "id": writeback.id,
                "project_id": project_id,
                "status": writeback.status,
                "accepted_asset_id": writeback.accepted_asset_id,
            }
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


@router.post("/{writeback_id}/reject")
def reject_writeback(project_id: str, writeback_id: str, session: Session = Depends(get_db_session)):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            writeback = WritebackService(session).reject(writeback_id)
            response = {"id": writeback.id, "project_id": project_id, "status": writeback.status}
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response
