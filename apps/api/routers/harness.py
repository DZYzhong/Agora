from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.runtime import CoreRuntime
from packages.harness.service import HarnessService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/harness", tags=["harness"])


class StartWorkRequest(BaseModel):
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


class CloseWorkRequest(BaseModel):
    session_id: str
    status: str = "closed"


def _harness(session: Session) -> HarnessService:
    context_engine = ContextEngine(keyword_index=FakeKeywordIndex(), vector_index=FakeVectorIndex())
    return HarnessService(core=CoreRuntime(session), context_engine=context_engine)


@router.post("/start-work")
def start_work(payload: StartWorkRequest, session: Session = Depends(get_db_session)):
    result = _harness(session).start_work(**payload.model_dump())
    if result.next_action == "ask_user":
        raise HTTPException(status_code=404, detail=result.clarification)
    return {
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


@router.post("/plan-context")
def plan_context(payload: PlanContextRequest, session: Session = Depends(get_db_session)):
    context = _harness(session).plan_context(**payload.model_dump())
    return context.__dict__


@router.post("/record-event")
def record_event(payload: RecordEventRequest, session: Session = Depends(get_db_session)):
    event = _harness(session).record_event(**payload.model_dump())
    return {"ok": True, "event": event}


@router.post("/close-work")
def close_work(payload: CloseWorkRequest, session: Session = Depends(get_db_session)):
    return _harness(session).close_work(**payload.model_dump())
