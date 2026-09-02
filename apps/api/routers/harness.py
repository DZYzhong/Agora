from typing import Any
import json
import re

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_project_member
from apps.api.dependencies import get_db_session, get_keyword_index, get_runtime_policy, get_vector_index
from apps.api.idempotency import execute_idempotent
from apps.api.routers.projects import _validate_local_initialization_path
from packages.core.auth import Principal
from packages.core.repositories.workflows import WorkflowStepError
from packages.core.settings import RuntimePolicy
from packages.core.upload_policy import (
    classify_upload,
    contains_secret,
    revalidate_upload,
)
from packages.core.services.protocol import (
    HARNESS_PROTOCOL_CURRENT,
    HARNESS_PROTOCOL_SUPPORTED,
    MINIMUM_LOCAL_CONNECTOR_VERSION,
    ProtocolContext,
    ProtocolNegotiationError,
    negotiate_protocol,
    protocol_deprecation,
    require_minimum_protocol,
)
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
    # PR1C low-risk workflow acknowledgment evidence: when present, the AI tool
    # asserts a local human confirmed this step (distinct from Approval).
    acknowledgment: dict[str, Any] | None = None

    @field_validator("acknowledgment")
    @classmethod
    def validate_acknowledgment_evidence(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        required = {
            "step_id",
            "prompt_digest",
            "choice",
            "local_interaction_id",
            "payload_digest",
            "policy_version",
            "acknowledged_at",
        }
        missing = sorted(required - set(value))
        if missing:
            raise ValueError(f"acknowledgment is missing required evidence fields: {', '.join(missing)}")
        return value


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


DEVELOPMENT_STATUSES = ("added", "modified", "deleted", "renamed")
MAX_CHANGED_FILES = 500
MAX_PATH_BYTES = 512
MAX_AGENT_SUMMARY_BYTES = 8 * 1024
MAX_TEST_RESULT_BYTES = 8 * 1024
MAX_DIFF_STAT_JSON_BYTES = 4 * 1024
_PATH_SECRET_PATTERN = re.compile(r"://|[\s]|[a-zA-Z][^/@\s]*:[^/@\s]*@")


class ChangedFilePathInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    status: str

    @field_validator("path")
    @classmethod
    def reject_unsafe_path(cls, value: str) -> str:
        if not value or value.startswith("/") or "\\" in value:
            raise ValueError("changed file path must be POSIX relative")
        parts = value.split("/")
        if any(part in ("", "..", ".") for part in parts):
            raise ValueError("changed file path must not contain traversal or empty segments")
        if any(ord(character) < 32 for character in value):
            raise ValueError("changed file path must not contain control characters")
        if len(value.encode("utf-8")) > MAX_PATH_BYTES:
            raise ValueError("changed file path exceeds 512 bytes")
        if _PATH_SECRET_PATTERN.search(value):
            raise ValueError("changed file path must not contain credentials or secret patterns")
        return value

    @field_validator("status")
    @classmethod
    def allowlist_status(cls, value: str) -> str:
        if value not in DEVELOPMENT_STATUSES:
            raise ValueError(f"unsupported change status: {value}")
        return value


class DevelopmentUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changed_files: list[ChangedFilePathInput] = Field(default_factory=list, max_length=MAX_CHANGED_FILES)
    dirty: bool = False
    diff_stat: dict[str, int] = Field(default_factory=dict)
    agent_summary: str | None = None
    test_result: str | None = None

    @field_validator("agent_summary")
    @classmethod
    def bound_agent_summary(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > MAX_AGENT_SUMMARY_BYTES:
            raise ValueError("agent_summary exceeds 8 KiB limit")
        return value

    @field_validator("test_result")
    @classmethod
    def bound_test_result(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > MAX_TEST_RESULT_BYTES:
            raise ValueError("test_result exceeds 8 KiB limit")
        return value

    @field_validator("diff_stat")
    @classmethod
    def bound_diff_stat(cls, value: dict[str, int]) -> dict[str, int]:
        encoded = json.dumps(value, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_DIFF_STAT_JSON_BYTES:
            raise ValueError("diff_stat exceeds 4 KiB limit")
        return value


class CloseWorkRequest(BaseModel):
    session_id: str
    status: str = "closed"
    development_update: DevelopmentUpdateInput | None = None
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


def _protocol_context(
    protocol_version: str | None = Header(default=None, alias="Agora-Protocol-Version"),
    connector_version: str | None = Header(default=None, alias="Agora-Connector-Version"),
) -> ProtocolContext:
    try:
        return negotiate_protocol(protocol_version, connector_version=connector_version)
    except ProtocolNegotiationError as exc:
        raise _upgrade_required(exc) from exc


def _upgrade_required(exc: ProtocolNegotiationError) -> HTTPException:
    detail = {
        "protocol_version": HARNESS_PROTOCOL_CURRENT,
        "request_id": None,
        "code": "UPGRADE_REQUIRED",
        "message": exc.message,
        "error": {"code": "UPGRADE_REQUIRED", "message": exc.message},
        "supported_protocol_versions": HARNESS_PROTOCOL_SUPPORTED,
        "current_protocol_version": HARNESS_PROTOCOL_CURRENT,
        "minimum_connector_version": MINIMUM_LOCAL_CONNECTOR_VERSION,
        "next_actions": [{"type": "upgrade_connector", "reason": exc.message}],
    }
    if exc.minimum_protocol_version is not None:
        detail["minimum_protocol_version"] = exc.minimum_protocol_version
    return HTTPException(status_code=426, detail=detail)


def _apply_protocol_metadata(response: dict, protocol: ProtocolContext) -> dict:
    response["protocol_version"] = protocol.protocol_version
    deprecation = protocol_deprecation(protocol)
    if deprecation is not None:
        existing = response.get("deprecation")
        response["deprecation"] = {**existing, **deprecation} if isinstance(existing, dict) else deprecation
    return response


@router.post("/start-work")
def start_work(
    payload: StartWorkRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    return execute_idempotent(
        session=session,
        principal=principal,
        protocol=protocol,
        operation="harness.start_work",
        idempotency_key=idempotency_key,
        request_payload=payload.model_dump(),
        callback=lambda initial_request_id: _execute_start_work(
            payload=payload,
            protocol=protocol,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
            initial_request_id=initial_request_id,
        ),
    )


@router.post("/plan-context")
def plan_context(
    payload: PlanContextRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
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
            _apply_protocol_metadata(response, protocol)
            uow.commit()
    except TokenBudgetTooSmall as exc:
        raise _protocol_error(
            "TOKEN_BUDGET_TOO_SMALL",
            str(exc),
            status_code=400,
            protocol=protocol,
            next_action_type="increase_token_budget",
        ) from exc
    return response


@router.post("/prepare-context")
def prepare_context(
    payload: PlanContextRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        return execute_idempotent(
            session=session,
            principal=principal,
            protocol=protocol,
            operation="harness.prepare_context",
            idempotency_key=idempotency_key,
            request_payload=payload.model_dump(),
            callback=lambda _initial_request_id: _prepare_context_once(
                payload=payload,
                protocol=protocol,
                principal=principal,
                session=session,
                keyword_index=keyword_index,
                vector_index=vector_index,
            ),
        )
    except TokenBudgetTooSmall as exc:
        raise _protocol_error(
            "TOKEN_BUDGET_TOO_SMALL",
            str(exc),
            status_code=400,
            protocol=protocol,
            next_action_type="increase_token_budget",
        ) from exc


def _prepare_context_once(
    *,
    payload: PlanContextRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    _ensure_session_member(session, principal, session_id=payload.session_id)
    response = _harness(session, keyword_index, vector_index).prepare_context(**payload.model_dump())
    _apply_protocol_metadata(response, protocol)
    return response


@router.post("/record-event")
def record_event(
    payload: RecordEventRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        event = _harness(session, keyword_index, vector_index).record_event(**payload.model_dump())
        response = {"ok": True, "event": event}
        _apply_protocol_metadata(response, protocol)
        uow.commit()
    return response


@router.post("/fetch-context-ref")
def fetch_context_ref(
    payload: FetchContextRefRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    try:
        _ensure_session_member(session, principal, session_id=payload.session_id)
        result = _harness(session, keyword_index, vector_index).fetch_context_ref(**payload.model_dump())
        return _apply_protocol_metadata(result.__dict__, protocol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submit-context-proposal", status_code=status.HTTP_201_CREATED)
def submit_context_proposal(
    payload: SubmitContextProposalRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    return execute_idempotent(
        session=session,
        principal=principal,
        protocol=protocol,
        operation="harness.submit_context_proposal",
        idempotency_key=idempotency_key,
        request_payload=payload.model_dump(),
        callback=lambda _initial_request_id: _submit_context_proposal_once(
            payload=payload,
            protocol=protocol,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
        ),
    )


def _submit_context_proposal_once(
    *,
    payload: SubmitContextProposalRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    task_session = _ensure_session_member(session, principal, session_id=payload.session_id)
    response = _harness(session, keyword_index, vector_index).submit_context_proposal(
        **payload.model_dump(),
        principal=principal,
        protocol_version=protocol.protocol_version,
    )
    response_dict = response.__dict__
    response_dict["request_id"] = task_session.id
    _apply_protocol_metadata(response_dict, protocol)
    return response_dict


@router.post("/complete-workflow-step")
def complete_workflow_step(
    payload: CompleteWorkflowStepRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
    runtime_policy: RuntimePolicy = Depends(get_runtime_policy),
):
    try:
        require_minimum_protocol(protocol, "1.1")
        return execute_idempotent(
            session=session,
            principal=principal,
            protocol=protocol,
            operation="harness.complete_workflow_step",
            idempotency_key=idempotency_key,
            request_payload=payload.model_dump(),
            callback=lambda _initial_request_id: _complete_workflow_step_once(
                payload=payload,
                protocol=protocol,
                principal=principal,
                session=session,
                keyword_index=keyword_index,
                vector_index=vector_index,
                runtime_policy=runtime_policy,
            ),
        )
    except ProtocolNegotiationError as exc:
        raise _upgrade_required(exc) from exc
    except WorkflowStepError as exc:
        raise _protocol_error(
            exc.code,
            str(exc),
            status_code=400,
            protocol=protocol,
            next_action_type="complete_current_workflow_step",
        ) from exc


def _complete_workflow_step_once(
    *,
    payload: CompleteWorkflowStepRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
    runtime_policy: RuntimePolicy,
) -> dict:
    _ensure_session_member(session, principal, session_id=payload.session_id)
    _enforce_pr1a_content_boundary(payload, runtime_policy)
    response = _harness(session, keyword_index, vector_index).complete_workflow_step(
        **payload.model_dump(),
        principal=principal,
        protocol_version=protocol.protocol_version,
    )
    response_dict = response.__dict__
    response_dict["request_id"] = payload.session_id
    _apply_protocol_metadata(response_dict, protocol)
    return response_dict


def _enforce_pr1a_content_boundary(payload: CompleteWorkflowStepRequest, runtime_policy: RuntimePolicy) -> None:
    """Temporary PR1A boundary: no untyped artifact upload or approval grants.

    Summary-only completions are always allowed when otherwise authorized.
    Artifacts and human confirmations are blocked in development and
    production; they remain accepted only in an isolated test environment.
    PR1B/PR1C replace these temporary errors with the typed upload/approval
    policies — the checks must never be removed blindly.
    """
    if runtime_policy.environment == "test":
        return
    if payload.artifacts:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PR1_UPLOAD_POLICY_REQUIRED",
                "message": "Work artifact upload requires the PR1B upload policy; summary-only completion is supported before then",
            },
        )
    if payload.human_confirmation is not None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PR1_APPROVAL_POLICY_REQUIRED",
                "message": "Approval grants require the PR1B approval policy; summary-only completion is supported before then",
            },
        )


@router.post("/submit-skill-candidate", status_code=status.HTTP_201_CREATED)
def submit_skill_candidate(
    payload: SubmitSkillCandidateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    return execute_idempotent(
        session=session,
        principal=principal,
        protocol=protocol,
        operation="harness.submit_skill_candidate",
        idempotency_key=idempotency_key,
        request_payload=payload.model_dump(),
        callback=lambda _initial_request_id: _submit_skill_candidate_once(
            payload=payload,
            protocol=protocol,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
        ),
    )


def _submit_skill_candidate_once(
    *,
    payload: SubmitSkillCandidateRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    _ensure_session_member(session, principal, session_id=payload.session_id)
    response = _harness(session, keyword_index, vector_index).submit_skill_candidate(
        **payload.model_dump(),
        principal=principal,
        protocol_version=protocol.protocol_version,
    )
    response_dict = response.__dict__
    response_dict["request_id"] = payload.session_id
    _apply_protocol_metadata(response_dict, protocol)
    return response_dict


@router.post("/suggest-skills")
def suggest_skills(
    payload: SuggestSkillsRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
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
            protocol_version=protocol.protocol_version,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        _apply_protocol_metadata(response_dict, protocol)
        uow.commit()
    return response_dict


@router.post("/record-evidence", status_code=status.HTTP_201_CREATED)
def record_evidence(
    payload: RecordEvidenceRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    return execute_idempotent(
        session=session,
        principal=principal,
        protocol=protocol,
        operation="harness.record_evidence",
        idempotency_key=idempotency_key,
        request_payload=payload.model_dump(),
        callback=lambda _initial_request_id: _record_evidence_once(
            payload=payload,
            protocol=protocol,
            principal=principal,
            session=session,
            keyword_index=keyword_index,
            vector_index=vector_index,
        ),
    )


def _record_evidence_once(
    *,
    payload: RecordEvidenceRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    _ensure_session_member(session, principal, session_id=payload.session_id)
    response = _harness(session, keyword_index, vector_index).record_evidence(
        **payload.model_dump(),
        principal=principal,
        protocol_version=protocol.protocol_version,
    )
    response_dict = response.__dict__
    response_dict["request_id"] = payload.session_id
    _apply_protocol_metadata(response_dict, protocol)
    return response_dict


@router.post("/get-quality-status")
def get_quality_status(
    payload: GetQualityStatusRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
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
            protocol_version=protocol.protocol_version,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.session_id
        _apply_protocol_metadata(response_dict, protocol)
        uow.commit()
    return response_dict


@router.post("/get-project-status")
def get_project_status(
    payload: GetProjectStatusRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        require_project_member(session, principal, project_id=payload.project_id)
        response = _harness(session, keyword_index, vector_index).get_project_status(
            **payload.model_dump(),
            principal=principal,
            protocol_version=protocol.protocol_version,
        )
        response_dict = response.__dict__
        response_dict["request_id"] = payload.project_id
        _apply_protocol_metadata(response_dict, protocol)
        uow.commit()
    return response_dict


@router.post("/close-work")
def close_work(
    payload: CloseWorkRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    protocol: ProtocolContext = Depends(_protocol_context),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
    runtime_policy: RuntimePolicy = Depends(get_runtime_policy),
):
    try:
        return execute_idempotent(
            session=session,
            principal=principal,
            protocol=protocol,
            operation="harness.close_work",
            idempotency_key=idempotency_key,
            request_payload=payload.model_dump(),
            callback=lambda _initial_request_id: _close_work_once(
                payload=payload,
                protocol=protocol,
                principal=principal,
                session=session,
                keyword_index=keyword_index,
                vector_index=vector_index,
                runtime_policy=runtime_policy,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _close_work_once(
    *,
    payload: CloseWorkRequest,
    protocol: ProtocolContext,
    principal: Principal,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
    runtime_policy: RuntimePolicy,
) -> dict:
    _ensure_session_member(session, principal, session_id=payload.session_id)
    _validate_close_work_capture(payload, protocol, runtime_policy)
    if payload.development_update is not None:
        _enforce_upload_policy_for_development_update(payload.development_update, principal)
    response = _harness(session, keyword_index, vector_index).close_work(
        session_id=payload.session_id,
        status=payload.status,
        development_update=payload.development_update.model_dump() if payload.development_update is not None else None,
        repo_path=payload.repo_path,
        base_ref=payload.base_ref,
        head_ref=payload.head_ref,
        agent_summary=payload.agent_summary,
        test_result=payload.test_result,
    )
    _apply_protocol_metadata(response, protocol)
    return response


def _enforce_upload_policy_for_development_update(
    update: DevelopmentUpdateInput,
    principal: Principal,
) -> None:
    """Server-side revalidation and tier/grant matching for close-work uploads."""
    violations = revalidate_upload(
        kind="development_update",
        paths=[entry.path for entry in update.changed_files],
        content=None,
        agent_summary=update.agent_summary,
        test_result=update.test_result,
        changed_files=len(update.changed_files),
        diff_stat_json=json.dumps(update.diff_stat, sort_keys=True) if update.diff_stat else None,
    )
    if violations:
        raise HTTPException(
            status_code=400,
            detail={"code": "UPLOAD_POLICY_VIOLATION", "message": "upload policy violation", "violations": violations},
        )

    high_risk_content = (
        contains_secret(update.agent_summary or "")
        or contains_secret(update.test_result or "")
    )
    assessment = classify_upload(
        kind="development_update",
        has_source_excerpt=high_risk_content,
        secret_rule_exception=high_risk_content,
    )
    if assessment.requires_grant and not principal.is_bypass:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "HIGH_RISK_UPLOAD_REQUIRES_GRANT",
                "message": "This development update is high-risk and requires a reauthenticated Web approval grant",
                "reasons": list(assessment.reasons),
            },
        )


def _validate_close_work_capture(
    payload: CloseWorkRequest,
    protocol: ProtocolContext,
    runtime_policy: RuntimePolicy,
) -> None:
    """Gate development capture: protocol 1.1 and production never touch server paths.

    Structured `development_update` from the Local Connector is always accepted
    (it is bounded and validated by the request model). Legacy `repo_path` is
    rejected under protocol 1.1, rejected in production before any Git access,
    and otherwise confined to an explicit local-init root.
    """
    if payload.repo_path is None:
        return
    if not protocol.legacy:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "LOCAL_REPO_PATH_REJECTED",
                "message": "Protocol 1.1 requires the Local Connector to capture the development update; server-local repository paths are not accepted",
            },
        )
    if runtime_policy.environment == "production":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "LOCAL_REPO_PATH_FORBIDDEN",
                "message": "Server-local repository capture is disabled in production",
            },
        )
    _validate_local_initialization_path(runtime_policy, payload.repo_path)


@router.post("/prepare-writeback")
def prepare_writeback(
    payload: PrepareWritebackRequest,
    protocol: ProtocolContext = Depends(_protocol_context),
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
        _apply_protocol_metadata(response, protocol)
        uow.commit()
    return response


def _ensure_session_member(session: Session, principal: Principal, *, session_id: str):
    runtime = CoreRuntime(session)
    task_session = runtime.get_session(session_id)
    if task_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    require_project_member(session, principal, project_id=task_session.project_id)
    return task_session


def _execute_start_work(
    *,
    payload: StartWorkRequest,
    protocol: ProtocolContext,
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
        raise _protocol_error(code, result.clarification or "Clarification required", status_code=404, protocol=protocol)
    return _serialize_start_work(result, protocol)


def _serialize_start_work(result, protocol: ProtocolContext) -> dict:
    next_action = {
        "type": result.next_action,
        "tool": "agora_prepare_context" if result.next_action == "plan_context" else None,
        "reason": result.clarification,
    }
    return _apply_protocol_metadata({
        "protocol_version": protocol.protocol_version,
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
    }, protocol)


def _protocol_error(
    code: str,
    message: str,
    *,
    status_code: int,
    protocol: ProtocolContext | None = None,
    legacy_code: str | None = None,
    next_action_type: str | None = None,
) -> HTTPException:
    action_type = next_action_type or ("clarify" if code in {"PROJECT_UNRESOLVED", "WORK_ITEM_CLARIFICATION_REQUIRED"} else "retry")
    protocol_version = protocol.protocol_version if protocol is not None else "1.0"
    return HTTPException(
        status_code=status_code,
        detail={
            "protocol_version": protocol_version,
            "request_id": None,
            "code": legacy_code or code,
            "message": message,
            "error": {"code": code, "message": message},
            "next_actions": [{"type": action_type, "reason": message}],
            "deprecation": {"legacy_error_fields": ["code", "message"], "remove_after": "P2"},
        },
    )
