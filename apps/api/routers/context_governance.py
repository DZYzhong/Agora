from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_human, require_project_approver, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.repositories.projects import ProjectRepository
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/projects/{project_id}/context", tags=["context-governance"])


class ContextProposalCreate(BaseModel):
    type: str = Field(pattern="^(initial|refresh|task_update|correction)$")
    title: str
    summary: str
    target_branch: str = "main"
    expected_head_revision_id: str | None = None
    from_commit_sha: str | None = None
    to_commit_sha: str | None = None
    work_item_id: str | None = None
    session_id: str | None = None
    content: dict = Field(default_factory=dict)
    source_anchors: list[dict] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)


class RevisionSignal(BaseModel):
    target_branch: str
    observed_head_sha: str | None = None
    contains_to_commit: bool = False
    merge_target_branch: str | None = None
    merged_to_target: bool = False


class ContextProposalApprove(BaseModel):
    expected_head_revision_id: str | None = None
    comment: str | None = None
    revision_signal: RevisionSignal


@router.get("/streams")
def list_context_streams(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    return [_serialize_stream(stream) for stream in CoreRuntime(session).list_context_streams_by_project(project_id)]


@router.get("/proposals")
def list_context_proposals(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    runtime = CoreRuntime(session)
    return [
        _serialize_proposal(runtime, proposal)
        for proposal in runtime.list_context_proposals_by_project(project_id)
    ]


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
def create_context_proposal(
    project_id: str,
    payload: ContextProposalCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)
        runtime = CoreRuntime(session)
        stream = runtime.ensure_context_stream(
            org_id=project.org_id,
            project_id=project.id,
            branch=payload.target_branch or project.default_branch or "main",
            repository_identity={"git_remotes": project.git_remotes},
        )
        proposal = runtime.create_context_proposal(
            org_id=project.org_id,
            project_id=project.id,
            stream_id=stream.id,
            work_item_id=payload.work_item_id,
            session_id=payload.session_id,
            type=payload.type,
            status="submitted",
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            source_anchors=payload.source_anchors,
            provenance=payload.provenance,
            target_branch=stream.branch,
            expected_head_revision_id=payload.expected_head_revision_id,
            from_commit_sha=payload.from_commit_sha,
            to_commit_sha=payload.to_commit_sha,
            created_by_user_id=principal.user_id,
        )
        response = _serialize_proposal(runtime, proposal)
        uow.commit()
    return response


@router.post("/proposals/{proposal_id}/approve")
def approve_context_proposal(
    project_id: str,
    proposal_id: str,
    payload: ContextProposalApprove,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        require_project_member(session, principal, project_id=project_id)
        runtime = CoreRuntime(session)
        proposal = runtime.get_context_proposal(proposal_id)
        if proposal is None or proposal.project_id != project_id:
            raise HTTPException(status_code=404, detail="Context proposal not found")
        stream = runtime.get_context_stream(proposal.stream_id)
        if stream is None or stream.project_id != project_id:
            raise HTTPException(status_code=404, detail="Context stream not found")
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if not principal.is_human:
            _record_security_audit(
                runtime,
                project=project,
                principal=principal,
                action="context_proposal.approve",
                target_type="context_proposal",
                target_id=proposal.id,
                decision="deny",
                reason="HUMAN_CREDENTIAL_REQUIRED",
            )
            uow.commit()
            require_human(principal)
        try:
            require_project_approver(session, principal, project_id=project_id)
        except HTTPException as exc:
            _record_security_audit(
                runtime,
                project=project,
                principal=principal,
                action="context_proposal.approve",
                target_type="context_proposal",
                target_id=proposal.id,
                decision="deny",
                reason="PROJECT_ROLE_REQUIRED",
                metadata={"detail": exc.detail},
            )
            uow.commit()
            raise
        if proposal.target_branch != stream.branch or payload.revision_signal.target_branch != stream.branch:
            raise HTTPException(status_code=400, detail="Revision signal branch does not match target stream")
        if proposal.to_commit_sha and not payload.revision_signal.contains_to_commit:
            raise HTTPException(status_code=400, detail="Target commit is not reachable from the revision signal")
        source_branch = proposal.provenance.get("source_branch")
        default_branch = project.default_branch or "main"
        if (
            stream.branch == default_branch
            and source_branch
            and source_branch != default_branch
            and (
                not payload.revision_signal.merged_to_target
                or payload.revision_signal.merge_target_branch != default_branch
            )
        ):
            raise HTTPException(
                status_code=400,
                detail="Feature branch context cannot update the default stream before merge reachability is proven",
            )
        expected_head = payload.expected_head_revision_id
        if expected_head != stream.head_revision_id or proposal.expected_head_revision_id != stream.head_revision_id:
            proposal.status = "needs_rebase"
            proposal.reviewed_by_user_id = principal.user_id
            proposal.review_comment = payload.comment
            response = {
                "proposal": _serialize_proposal(runtime, proposal),
                "stream": _serialize_stream(stream),
            }
            uow.commit()
            return JSONResponse(status_code=409, content=jsonable_encoder(response))
        revision = runtime.create_context_revision(
            org_id=proposal.org_id,
            project_id=proposal.project_id,
            stream_id=stream.id,
            schema_version=proposal.provenance.get("schema_version", "context-revision/v1"),
            parent_revision_id=stream.head_revision_id,
            commit_sha=proposal.to_commit_sha,
            content=proposal.content,
            source_anchors=proposal.source_anchors,
            provenance={
                **proposal.provenance,
                "approved_by_user_id": principal.user_id,
                "proposal_id": proposal.id,
                "revision_signal": payload.revision_signal.model_dump(),
            },
            created_by_user_id=proposal.created_by_user_id,
        )
        stream.head_revision_id = revision.id
        proposal.status = "approved"
        proposal.reviewed_by_user_id = principal.user_id
        proposal.review_comment = payload.comment
        proposal.accepted_revision_id = revision.id
        decision = runtime.create_approval_decision(
            org_id=proposal.org_id,
            project_id=proposal.project_id,
            proposal_id=proposal.id,
            decision="approved",
            comment=payload.comment,
            decided_by_user_id=principal.user_id,
        )
        _record_security_audit(
            runtime,
            project=project,
            principal=principal,
            action="context_proposal.approve",
            target_type="context_proposal",
            target_id=proposal.id,
            decision="allow",
            reason="PROJECT_APPROVER",
            metadata={"approval_decision_id": decision.id, "revision_id": revision.id},
        )
        outbox_event = runtime.create_outbox_event(
            org_id=proposal.org_id,
            aggregate_type="context_stream",
            aggregate_id=stream.id,
            type="context_head_changed",
            payload={
                "project_id": project_id,
                "stream_id": stream.id,
                "revision_id": revision.id,
                "proposal_id": proposal.id,
            },
            status="pending",
            attempts=0,
            idempotency_key=f"context_head_changed:{stream.id}:{revision.id}",
        )
        response = {
            "proposal": _serialize_proposal(runtime, proposal),
            "stream": _serialize_stream(stream),
            "revision": _serialize_revision(revision),
            "approval_decision": {
                "id": decision.id,
                "decision": decision.decision,
                "comment": decision.comment,
            },
            "outbox_event": {
                "id": outbox_event.id,
                "type": outbox_event.type,
                "status": outbox_event.status,
            },
        }
        uow.commit()
    return response


def _record_security_audit(
    runtime: CoreRuntime,
    *,
    project,
    principal: Principal,
    action: str,
    target_type: str,
    target_id: str,
    decision: str,
    reason: str,
    metadata: dict | None = None,
) -> None:
    runtime.create_security_audit_event(
        org_id=project.org_id,
        project_id=project.id,
        actor_user_id=principal.user_id,
        actor_credential_id=None if principal.is_bypass else principal.credential_id,
        actor_credential_kind=principal.credential_kind,
        action=action,
        target_type=target_type,
        target_id=target_id,
        decision=decision,
        reason=reason,
        metadata=metadata or {},
    )


def _serialize_stream(stream) -> dict:
    return {
        "id": stream.id,
        "project_id": stream.project_id,
        "name": stream.name,
        "branch": stream.branch,
        "head_revision_id": stream.head_revision_id,
        "status": stream.status,
        "repository_identity": stream.repository_identity,
        "created_at": stream.created_at,
        "updated_at": stream.updated_at,
    }


def _serialize_revision(revision) -> dict:
    return {
        "id": revision.id,
        "project_id": revision.project_id,
        "stream_id": revision.stream_id,
        "schema_version": revision.schema_version,
        "parent_revision_id": revision.parent_revision_id,
        "commit_sha": revision.commit_sha,
        "content": revision.content,
        "source_anchors": revision.source_anchors,
        "provenance": revision.provenance,
        "created_at": revision.created_at,
    }


def _serialize_proposal(runtime: CoreRuntime, proposal) -> dict:
    stream = runtime.get_context_stream(proposal.stream_id)
    return {
        "id": proposal.id,
        "project_id": proposal.project_id,
        "stream_id": proposal.stream_id,
        "stream": _serialize_stream(stream) if stream else None,
        "work_item_id": proposal.work_item_id,
        "session_id": proposal.session_id,
        "type": proposal.type,
        "status": proposal.status,
        "title": proposal.title,
        "summary": proposal.summary,
        "content": proposal.content,
        "source_anchors": proposal.source_anchors,
        "provenance": proposal.provenance,
        "target_branch": proposal.target_branch,
        "expected_head_revision_id": proposal.expected_head_revision_id,
        "from_commit_sha": proposal.from_commit_sha,
        "to_commit_sha": proposal.to_commit_sha,
        "accepted_revision_id": proposal.accepted_revision_id,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
    }
