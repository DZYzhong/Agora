from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.harness.service import HarnessService
from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/harness", tags=["harness"])


class StartWorkRequest(BaseModel):
    project_id: str | None = None
    user_message: str
    repo_remote: str | None = None
    agent_type: str


class PlanContextRequest(BaseModel):
    session_id: str
    query: str | None = None
    token_budget: int = 4000


class RecordEventRequest(BaseModel):
    session_id: str
    event_type: str
    payload: dict[str, Any]


class FetchContextRefRequest(BaseModel):
    session_id: str
    asset_id: str
    max_tokens: int = 2000


class CloseWorkRequest(BaseModel):
    session_id: str
    status: str = "closed"
    repo_path: str | None = None
    base_ref: str = "HEAD"
    head_ref: str | None = None
    agent_summary: str | None = None
    test_result: str | None = None


class PrepareWritebackRequest(BaseModel):
    session_id: str
    type: str
    title: str
    content: str
    asset_refs: list[str] = []


def _harness(session: Session, keyword_index: FakeKeywordIndex, vector_index: FakeVectorIndex) -> HarnessService:
    context_engine = ContextEngine(keyword_index=keyword_index, vector_index=vector_index)
    return HarnessService(core=CoreRuntime(session), context_engine=context_engine)


@router.post("/start-work")
def start_work(
    payload: StartWorkRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        result = _harness(session, keyword_index, vector_index).start_work(**payload.model_dump())
        if result.next_action == "ask_user":
            raise HTTPException(status_code=404, detail=result.clarification)
        response = {
            "session_id": result.session_id,
            "project": {
                "id": result.project.id,
                "org_id": result.project.org_id,
                "name": result.project.name,
                "slug": result.project.slug,
            },
            "task_id": result.task_id,
            "intent": result.intent,
            "next_action": result.next_action,
        }
        uow.commit()
    return response


@router.post("/plan-context")
def plan_context(
    payload: PlanContextRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        context = _harness(session, keyword_index, vector_index).plan_context(**payload.model_dump())
        response = context.__dict__
        uow.commit()
    return response


@router.post("/record-event")
def record_event(
    payload: RecordEventRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        event = _harness(session, keyword_index, vector_index).record_event(**payload.model_dump())
        response = {"ok": True, "event": event}
        uow.commit()
    return response


@router.post("/fetch-context-ref")
def fetch_context_ref(
    payload: FetchContextRefRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        result = _harness(session, keyword_index, vector_index).fetch_context_ref(**payload.model_dump())
        return result.__dict__
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/close-work")
def close_work(
    payload: CloseWorkRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            response = _harness(session, keyword_index, vector_index).close_work(**payload.model_dump())
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return response


@router.post("/prepare-writeback")
def prepare_writeback(
    payload: PrepareWritebackRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        task_session = runtime.get_session(payload.session_id)
        if task_session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        service = MemoryWritebackService(core=runtime, keyword_index=keyword_index, vector_index=vector_index)
        writeback = service.prepare_writeback(
            org_id=task_session.org_id,
            project_id=task_session.project_id,
            session_id=payload.session_id,
            type=payload.type,
            title=payload.title,
            content=payload.content,
            asset_refs=payload.asset_refs,
        )
        response = {
            "id": writeback.id,
            "project_id": writeback.project_id,
            "session_id": writeback.session_id,
            "type": writeback.type,
            "title": writeback.title,
            "content": writeback.content,
            "status": writeback.status,
        }
        uow.commit()
    return response
