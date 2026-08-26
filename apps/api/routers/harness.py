from typing import Any
from datetime import timedelta
import hashlib
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_project_member
from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from packages.core.auth import Principal
from packages.core.models import utc_now
from packages.core.repositories.workflows import WorkflowStepError
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.domain.local_workspace import LocalWorkspaceObservation
from packages.harness.context_bundle import TokenBudgetTooSmall
from packages.harness.service import HarnessService
from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/harness", tags=["harness"])


class StartWorkRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str | None = None
    user_message: str
    repo_remote: str | None = None
    agent_type: str
    branch_name: str | None = None
    local_observation: LocalWorkspaceObservation | None = None

    @field_validator("repo_remote")
    @classmethod
    def reject_path_like_remote(cls, value: str | None) -> str | None:
        if value and (value.startswith("/") or "\\" in value):
            raise ValueError("repo_remote must not be a local path")
        return value


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


class SubmitContextProposalRequest(BaseModel):
    session_id: str
    type: str = Field(pattern="^(initial|refresh|task_update|correction)$")
    title: str
    summary: str
    target_branch: str = "main"
    expected_head_revision_id: str | None = None
    from_commit_sha: str | None = None
    to_commit_sha: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    source_anchors: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CompleteWorkflowStepRequest(BaseModel):
    session_id: str
    step_key: str
    summary: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    human_confirmation: dict[str, Any] | None = None


class SubmitSkillCandidateRequest(BaseModel):
    session_id: str
    slug: str
    name: str
    summary: str
    triggers: list[str] = Field(default_factory=list)
    instructions: str
    artifact_ids: list[str] = Field(default_factory=list)


class SuggestSkillsRequest(BaseModel):
    session_id: str
    query: str | None = None


class RecordEvidenceRequest(BaseModel):
    session_id: str
    evidence_type: str
    source: str
    status: str
    conclusion: str
    command: str | None = None
    output_summary: str | None = None
    raw_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GetQualityStatusRequest(BaseModel):
    session_id: str
    scope: str = "work_item"


class GetProjectStatusRequest(BaseModel):
    project_id: str


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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    if idempotency_key:
        return _start_work_idempotent(
            payload=payload,
            idempotency_key=idempotency_key,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
        )

    with SqlAlchemyUnitOfWork(session) as uow:
        response = _execute_start_work(
            payload=payload,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
            initial_request_id=None,
        )
        uow.commit()
    return response


@router.post("/plan-context")
def plan_context(
    payload: PlanContextRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            _ensure_session_member(session, principal, session_id=payload.session_id)
            response = _harness(session, keyword_index, vector_index).prepare_context(
                **payload.model_dump(),
                event_type="context_planned",
            )
            response["deprecation"] = {
                "legacy_endpoint": "/harness/plan-context",
                "canonical_endpoint": "/harness/prepare-context",
                "remove_after": "P2",
            }
            uow.commit()
    except TokenBudgetTooSmall as exc:
        raise _protocol_error(
            "TOKEN_BUDGET_TOO_SMALL",
            str(exc),
            status_code=400,
            next_action_type="increase_token_budget",
        ) from exc
    return response


@router.post("/prepare-context")
def prepare_context(
    payload: PlanContextRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            _ensure_session_member(session, principal, session_id=payload.session_id)
            response = _harness(session, keyword_index, vector_index).prepare_context(**payload.model_dump())
            uow.commit()
    except TokenBudgetTooSmall as exc:
        raise _protocol_error(
            "TOKEN_BUDGET_TOO_SMALL",
            str(exc),
            status_code=400,
            next_action_type="increase_token_budget",
        ) from exc
    return response


@router.post("/record-event")
def record_event(
    payload: RecordEventRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        event = _harness(session, keyword_index, vector_index).record_event(**payload.model_dump())
        response = {"ok": True, "event": event}
        uow.commit()
    return response


@router.post("/fetch-context-ref")
def fetch_context_ref(
    payload: FetchContextRefRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        result = _harness(session, keyword_index, vector_index).fetch_context_ref(**payload.model_dump())
        return result.__dict__
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submit-context-proposal", status_code=status.HTTP_201_CREATED)
def submit_context_proposal(
    payload: SubmitContextProposalRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        task_session = _ensure_session_member(session, principal, session_id=payload.session_id)
        response = _harness(session, keyword_index, vector_index).submit_context_proposal(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = task_session.id
        uow.commit()
    return response_dict


@router.post("/complete-workflow-step")
def complete_workflow_step(
    payload: CompleteWorkflowStepRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            _ensure_session_member(session, principal, session_id=payload.session_id)
            response = _harness(session, keyword_index, vector_index).complete_workflow_step(
                **payload.model_dump(),
                principal=principal,
            )
            response_dict = response.__dict__
            response_dict["request_id"] = payload.session_id
            uow.commit()
    except WorkflowStepError as exc:
        raise _protocol_error(
            exc.code,
            str(exc),
            status_code=400,
            next_action_type="complete_current_workflow_step",
        ) from exc
    return response_dict


@router.post("/submit-skill-candidate", status_code=status.HTTP_201_CREATED)
def submit_skill_candidate(
    payload: SubmitSkillCandidateRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        response = _harness(session, keyword_index, vector_index).submit_skill_candidate(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        uow.commit()
    return response_dict


@router.post("/suggest-skills")
def suggest_skills(
    payload: SuggestSkillsRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        response = _harness(session, keyword_index, vector_index).suggest_skills(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        uow.commit()
    return response_dict


@router.post("/record-evidence", status_code=status.HTTP_201_CREATED)
def record_evidence(
    payload: RecordEvidenceRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        response = _harness(session, keyword_index, vector_index).record_evidence(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        uow.commit()
    return response_dict


@router.post("/get-quality-status")
def get_quality_status(
    payload: GetQualityStatusRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        response = _harness(session, keyword_index, vector_index).get_quality_status(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        uow.commit()
    return response_dict


@router.post("/get-project-status")
def get_project_status(
    payload: GetProjectStatusRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    require_project_member(session, principal, project_id=payload.project_id)
    with SqlAlchemyUnitOfWork(session) as uow:
        response = _harness(session, keyword_index, vector_index).get_project_status(
            **payload.model_dump(),
            principal=principal,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.project_id
        uow.commit()
    return response_dict


@router.post("/close-work")
def close_work(
    payload: CloseWorkRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            _ensure_session_member(session, principal, session_id=payload.session_id)
            response = _harness(session, keyword_index, vector_index).close_work(**payload.model_dump())
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return response


@router.post("/prepare-writeback")
def prepare_writeback(
    payload: PrepareWritebackRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        task_session = runtime.get_session(payload.session_id)
        if task_session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        require_project_member(session, principal, project_id=task_session.project_id)
        service = MemoryWritebackService(core=runtime)
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


def _ensure_session_member(session: Session, principal: Principal, *, session_id: str):
    runtime = CoreRuntime(session)
    task_session = runtime.get_session(session_id)
    if task_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    require_project_member(session, principal, project_id=task_session.project_id)
    return task_session


def _start_work_idempotent(
    *,
    payload: StartWorkRequest,
    idempotency_key: str,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    operation = "harness.start_work"
    request_hash = _request_hash(payload)
    pending_error: HTTPException | None = None
    for _ in range(10):
        pending = False
        try:
            with SqlAlchemyUnitOfWork(session) as uow:
                runtime = CoreRuntime(session)
                record = runtime.get_idempotency_record(
                    credential_id=principal.credential_id,
                    operation=operation,
                    idempotency_key=idempotency_key,
                )
                if record is not None:
                    if record.status == "expired" or _replay_expired(record.replay_expires_at):
                        record.status = "expired"
                        uow.commit()
                        pending_error = _idempotency_error("IDEMPOTENCY_KEY_EXPIRED", "Idempotency key has expired")
                    elif record.request_hash != request_hash:
                        pending_error = _idempotency_error("IDEMPOTENCY_CONFLICT", "Idempotency key payload changed")
                    elif record.status == "completed" and record.response_json is not None:
                        response = record.response_json
                        uow.commit()
                        return response
                    else:
                        pending = True
                else:
                    record = runtime.create_idempotency_record(
                        user_id=principal.user_id,
                        credential_id=principal.credential_id,
                        operation=operation,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        replay_window=timedelta(hours=24),
                    )
                    response = _execute_start_work(
                        payload=payload,
                        principal=principal,
                        session=session,
                        keyword_index=keyword_index,
                        vector_index=vector_index,
                        initial_request_id=record.id,
                    )
                    runtime.complete_idempotency_record(record, response_json=response)
                    uow.commit()
                    return response
        except (IntegrityError, OperationalError):
            if session.in_transaction():
                session.rollback()
            time.sleep(0.05)
            continue

        if pending_error is not None:
            raise pending_error
        if pending:
            time.sleep(0.05)
            continue
    raise _idempotency_error("IDEMPOTENCY_REPLAY_PENDING", "Idempotency replay is still pending")


def _execute_start_work(
    *,
    payload: StartWorkRequest,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
    initial_request_id: str | None,
) -> dict:
    if payload.project_id is not None:
        require_project_member(session, principal, project_id=payload.project_id)
    result = _harness(session, keyword_index, vector_index).start_work(
        **payload.model_dump(),
        principal=principal,
        initial_request_id=initial_request_id,
    )
    if result.project is not None:
        require_project_member(session, principal, project_id=result.project.id)
    if result.next_action == "ask_user":
        code = "WORK_ITEM_CLARIFICATION_REQUIRED" if result.project is not None else "PROJECT_UNRESOLVED"
        raise _protocol_error(code, result.clarification or "Clarification required", status_code=404)
    return _serialize_start_work(result)


def _serialize_start_work(result) -> dict:
    next_action = {
        "type": result.next_action,
        "tool": "agora_prepare_context" if result.next_action == "plan_context" else None,
        "reason": result.clarification,
    }
    return {
        "protocol_version": "1.0",
        "request_id": result.session_id,
        "capabilities": {
            "local_repository_observation": True,
            "work_items": True,
            "context_revisions": True,
            "skills": True,
            "quality_evidence": True,
        },
        "session_id": result.session_id,
        "work_item_id": result.work_item_id,
        "work_item_title": result.work_item_title,
        "project": {
            "id": result.project.id,
            "org_id": result.project.org_id,
            "name": result.project.name,
            "slug": result.project.slug,
        },
        "task_id": result.task_id,
        "intent": result.intent,
        "next_action": result.next_action,
        "next_actions": [next_action],
        "context_revision_id": result.context_revision_id,
        "workflow_version_id": result.workflow_version_id,
        "skill_version_id": result.skill_version_id,
    }


def _request_hash(payload: StartWorkRequest) -> str:
    encoded = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _replay_expired(replay_expires_at) -> bool:
    now = utc_now()
    if replay_expires_at.tzinfo is None:
        return replay_expires_at <= now.replace(tzinfo=None)
    return replay_expires_at <= now


def _idempotency_error(code: str, message: str) -> HTTPException:
    mapped_code = "IDEMPOTENCY_CONFLICT" if code.startswith("IDEMPOTENCY") else code
    return _protocol_error(mapped_code, message, status_code=409, legacy_code=code)


def _protocol_error(
    code: str,
    message: str,
    *,
    status_code: int,
    legacy_code: str | None = None,
    next_action_type: str | None = None,
) -> HTTPException:
    action_type = next_action_type or ("clarify" if code in {"PROJECT_UNRESOLVED", "WORK_ITEM_CLARIFICATION_REQUIRED"} else "retry")
    return HTTPException(
        status_code=status_code,
        detail={
            "protocol_version": "1.0",
            "request_id": None,
            "code": legacy_code or code,
            "message": message,
            "error": {"code": code, "message": message},
            "next_actions": [{"type": action_type, "reason": message}],
            "deprecation": {"legacy_error_fields": ["code", "message"], "remove_after": "P2"},
        },
    )
