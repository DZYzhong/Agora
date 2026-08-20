import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_human, require_project_member
from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from packages.core.auth import Principal
from packages.core.services.runtime import CoreRuntime
from packages.core.services.writebacks import WritebackService
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.harness.memory_writeback import MemoryWritebackService
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/projects/{project_id}/writebacks", tags=["writebacks"])
logger = logging.getLogger(__name__)


@router.get("")
def list_writebacks(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
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
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    require_human(principal)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            require_project_member(session, principal, project_id=project_id)
            service = MemoryWritebackService(core=CoreRuntime(session))
            result = service.accept_writeback(writeback_id)
            writeback = result.writeback
            if writeback.project_id != project_id:
                raise HTTPException(status_code=404, detail="Writeback not found")
            response = {
                "id": writeback.id,
                "project_id": project_id,
                "status": writeback.status,
                "accepted_asset_id": writeback.accepted_asset_id,
                "index_status": "indexed",
                "warnings": [],
            }
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    warnings = []
    for index_name, index in (("keyword", keyword_index), ("vector", vector_index)):
        try:
            index.index_asset(result.pending_index.asset_id, result.pending_index.asset)
        except Exception as exc:
            logger.exception("Post-commit %s index refresh failed for writeback %s", index_name, writeback_id)
            warnings.append(f"{index_name} index pending_rebuild: {exc}")
    if warnings:
        response["index_status"] = "pending_rebuild"
        response["warnings"] = warnings
    return response


@router.post("/{writeback_id}/reject")
def reject_writeback(
    project_id: str,
    writeback_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            require_project_member(session, principal, project_id=project_id)
            writeback = WritebackService(session).reject(writeback_id)
            if writeback.project_id != project_id:
                raise HTTPException(status_code=404, detail="Writeback not found")
            response = {"id": writeback.id, "project_id": project_id, "status": writeback.status}
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response
