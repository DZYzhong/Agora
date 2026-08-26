import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_ci, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.harness.service import HarnessService

router = APIRouter(prefix="/integrations", tags=["integrations"])


class CiQualitySignalRequest(BaseModel):
    project_id: str
    work_item_key: str
    work_item_title: str | None = None
    status: str = Field(pattern="^(passed|failed|warning|unknown)$")
    conclusion: str
    command: str | None = None
    output_summary: str | None = None
    provider: str = "ci"
    run_id: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    raw_ref: str | None = None
    task_provider: str | None = None
    task_key: str | None = None
    task_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RepositoryRevisionSignalRequest(BaseModel):
    project_id: str
    provider: str
    repository_identity: str
    branch: str = "main"
    observed_head_sha: str
    previous_head_sha: str | None = None
    signal_type: str = "push"
    work_item_key: str | None = None
    work_item_title: str | None = None
    raw_ref: str | None = None
    task_provider: str | None = None
    task_key: str | None = None
    task_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PullRequestSignalRequest(BaseModel):
    project_id: str | None = None
    provider: str
    repository_identity: str
    pull_request_id: str
    pull_request_url: str | None = None
    title: str | None = None
    action: str = Field(pattern="^(opened|updated|approved|merged|closed)$")
    source_branch: str | None = None
    target_branch: str = "main"
    head_sha: str | None = None
    merge_commit_sha: str | None = None
    work_item_key: str | None = None
    work_item_title: str | None = None
    task_provider: str | None = None
    task_key: str | None = None
    task_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/ci/quality-signal", status_code=status.HTTP_201_CREATED)
def ingest_ci_quality_signal(
    payload: CiQualitySignalRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_ci(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        project = runtime.get_project(payload.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)
        work_item = runtime.get_work_item_by_external_key(project_id=project.id, external_key=payload.work_item_key)
        if work_item is None:
            work_item = runtime.create_work_item(
                org_id=project.org_id,
                project_id=project.id,
                external_key=payload.work_item_key,
                title=payload.work_item_title or payload.work_item_key,
                source="ci",
            )
        task_link = _upsert_task_link(
            runtime=runtime,
            project=project,
            work_item=work_item,
            principal=principal,
            task_provider=payload.task_provider,
            task_key=payload.task_key or payload.work_item_key,
            task_url=payload.task_url,
            title=payload.work_item_title or payload.work_item_key,
            metadata={"source": "ci_quality_signal", "ci_provider": payload.provider, "run_id": payload.run_id},
        )
        evidence = runtime.create_quality_evidence(
            org_id=project.org_id,
            project_id=project.id,
            work_item_id=work_item.id,
            session_id=None,
            evidence_type="ci",
            source="ci",
            status=payload.status,
            conclusion=payload.conclusion,
            command=payload.command,
            output_summary=payload.output_summary,
            raw_ref=payload.raw_ref,
            metadata={
                **payload.metadata,
                "provider": payload.provider,
                "run_id": payload.run_id,
                "commit_sha": payload.commit_sha,
                "branch": payload.branch,
            },
            created_by_user_id=principal.user_id,
        )
        project_status = HarnessService(core=runtime, context_engine=None).get_project_status(
            project_id=project.id,
            principal=principal,
        )
        response = {
            "protocol_version": "1.0",
            "operation": "ingest_ci_quality_signal",
            "project": {
                "id": project.id,
                "slug": project.slug,
                "name": project.name,
            },
            "work_item": {
                "id": work_item.id,
                "external_key": work_item.external_key,
                "title": work_item.title,
                "status": work_item.status,
                "stage": work_item.stage,
            },
            "task_link": _serialize_work_item_link(task_link) if task_link is not None else None,
            "evidence": _serialize_quality_evidence(evidence),
            "project_status": project_status.__dict__,
        }
        uow.commit()
    return response


@router.post("/repository/pull-request-signal", status_code=status.HTTP_201_CREATED)
def ingest_pull_request_signal(
    payload: PullRequestSignalRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_ci(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        project = _resolve_project(runtime, payload.project_id, payload.repository_identity)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)
        work_item_key = _resolve_work_item_key(
            explicit_key=payload.work_item_key or payload.task_key,
            task_url=payload.task_url,
            source_branch=payload.source_branch,
            title=payload.title,
        )
        work_item = None
        if work_item_key:
            work_item = runtime.get_work_item_by_external_key(project_id=project.id, external_key=work_item_key)
            if work_item is None:
                work_item = runtime.create_work_item(
                    org_id=project.org_id,
                    project_id=project.id,
                    external_key=work_item_key,
                    title=payload.work_item_title or payload.title or work_item_key,
                    source="pull_request_signal",
                )
        task_link = None
        if work_item is not None:
            task_link = _upsert_task_link(
                runtime=runtime,
                project=project,
                work_item=work_item,
                principal=principal,
                task_provider=payload.task_provider,
                task_key=payload.task_key or work_item_key,
                task_url=payload.task_url,
                title=payload.work_item_title or payload.title or work_item_key,
                metadata={
                    "source": "pull_request_signal",
                    "repository_provider": payload.provider,
                    "pull_request_id": payload.pull_request_id,
                },
            )
        signal_status = "merged" if payload.action == "merged" else "observed"
        pr_signal = runtime.create_pull_request_signal(
            org_id=project.org_id,
            project_id=project.id,
            work_item_id=work_item.id if work_item is not None else None,
            provider=payload.provider,
            repository_identity=payload.repository_identity,
            pull_request_id=payload.pull_request_id,
            pull_request_url=payload.pull_request_url,
            title=payload.title,
            action=payload.action,
            source_branch=payload.source_branch,
            target_branch=payload.target_branch or project.default_branch or "main",
            head_sha=payload.head_sha,
            merge_commit_sha=payload.merge_commit_sha,
            status=signal_status,
            metadata=payload.metadata,
            created_by_user_id=principal.user_id,
        )
        observed_sha = payload.merge_commit_sha if payload.action == "merged" else payload.head_sha
        context_freshness = {"state": "not_evaluated"}
        proposal = None
        if payload.action == "merged" and observed_sha:
            context_freshness, proposal = _create_refresh_proposal_for_observed_head(
                runtime=runtime,
                project=project,
                work_item=work_item,
                principal=principal,
                branch=payload.target_branch or project.default_branch or "main",
                repository_identity=payload.repository_identity,
                provider=payload.provider,
                observed_head_sha=observed_sha,
                previous_head_sha=payload.head_sha,
                reason="pull_request_signal",
                signal_id=pr_signal.id,
            )
        response = {
            "protocol_version": "1.0",
            "operation": "ingest_pull_request_signal",
            "project": {
                "id": project.id,
                "slug": project.slug,
                "name": project.name,
            },
            "pull_request_signal": _serialize_pull_request_signal(pr_signal),
            "context_freshness": context_freshness,
            "work_item": _serialize_work_item(work_item) if work_item is not None else None,
            "task_link": _serialize_work_item_link(task_link) if task_link is not None else None,
            "context_proposal": _serialize_context_proposal(proposal) if proposal is not None else None,
            "next_actions": _pull_request_next_actions(payload.action, context_freshness.get("state")),
        }
        uow.commit()
    return response


@router.post("/repository/revision-signal", status_code=status.HTTP_201_CREATED)
def ingest_repository_revision_signal(
    payload: RepositoryRevisionSignalRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_ci(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        project = runtime.get_project(payload.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)
        work_item = None
        if payload.work_item_key:
            work_item = runtime.get_work_item_by_external_key(project_id=project.id, external_key=payload.work_item_key)
            if work_item is None:
                work_item = runtime.create_work_item(
                    org_id=project.org_id,
                    project_id=project.id,
                    external_key=payload.work_item_key,
                    title=payload.work_item_title or payload.work_item_key,
                    source="repository_signal",
                )
        task_link = None
        if work_item is not None:
            task_link = _upsert_task_link(
                runtime=runtime,
                project=project,
                work_item=work_item,
                principal=principal,
                task_provider=payload.task_provider,
                task_key=payload.task_key or payload.work_item_key,
                task_url=payload.task_url,
                title=payload.work_item_title or payload.work_item_key,
                metadata={
                    "source": "repository_revision_signal",
                    "repository_provider": payload.provider,
                    "observed_head_sha": payload.observed_head_sha,
                },
            )
        branch = payload.branch or project.default_branch or "main"
        head_revision = runtime.get_head_context_revision_for_project(project_id=project.id, branch=branch)
        signal_status = _freshness_signal_status(head_revision, payload.observed_head_sha)
        freshness_state = _freshness_state(signal_status)
        signal = runtime.create_repository_revision_signal(
            org_id=project.org_id,
            project_id=project.id,
            work_item_id=work_item.id if work_item is not None else None,
            provider=payload.provider,
            repository_identity=payload.repository_identity,
            branch=branch,
            observed_head_sha=payload.observed_head_sha,
            previous_head_sha=payload.previous_head_sha,
            signal_type=payload.signal_type,
            status=signal_status,
            raw_ref=payload.raw_ref,
            metadata=payload.metadata,
            created_by_user_id=principal.user_id,
        )
        proposal = None
        if signal_status == "stale_context":
            context_freshness, proposal = _create_refresh_proposal_for_observed_head(
                runtime=runtime,
                project=project,
                work_item=work_item,
                principal=principal,
                branch=branch,
                repository_identity=payload.repository_identity,
                provider=payload.provider,
                observed_head_sha=payload.observed_head_sha,
                previous_head_sha=payload.previous_head_sha,
                reason="repository_revision_signal",
                signal_id=signal.id,
            )
        else:
            context_freshness = _serialize_context_freshness(freshness_state, branch, head_revision, payload.observed_head_sha)
        response = {
            "protocol_version": "1.0",
            "operation": "ingest_repository_revision_signal",
            "signal": _serialize_repository_revision_signal(signal),
            "context_freshness": context_freshness,
            "work_item": _serialize_work_item(work_item) if work_item is not None else None,
            "task_link": _serialize_work_item_link(task_link) if task_link is not None else None,
            "context_proposal": _serialize_context_proposal(proposal) if proposal is not None else None,
            "next_actions": _revision_signal_next_actions(signal_status),
        }
        uow.commit()
    return response


def _serialize_quality_evidence(evidence) -> dict:
    return {
        "id": evidence.id,
        "project_id": evidence.project_id,
        "work_item_id": evidence.work_item_id,
        "session_id": evidence.session_id,
        "evidence_type": evidence.evidence_type,
        "source": evidence.source,
        "status": evidence.status,
        "conclusion": evidence.conclusion,
        "command": evidence.command,
        "output_summary": evidence.output_summary,
        "raw_ref": evidence.raw_ref,
        "metadata": evidence.evidence_metadata,
        "created_by_user_id": evidence.created_by_user_id,
        "created_at": evidence.created_at,
        "classification": "evidence",
    }


def _serialize_repository_revision_signal(signal) -> dict:
    return {
        "id": signal.id,
        "project_id": signal.project_id,
        "work_item_id": signal.work_item_id,
        "provider": signal.provider,
        "repository_identity": signal.repository_identity,
        "branch": signal.branch,
        "observed_head_sha": signal.observed_head_sha,
        "previous_head_sha": signal.previous_head_sha,
        "signal_type": signal.signal_type,
        "status": signal.status,
        "raw_ref": signal.raw_ref,
        "metadata": signal.signal_metadata,
        "created_by_user_id": signal.created_by_user_id,
        "created_at": signal.created_at,
    }


def _serialize_pull_request_signal(signal) -> dict:
    return {
        "id": signal.id,
        "project_id": signal.project_id,
        "work_item_id": signal.work_item_id,
        "provider": signal.provider,
        "repository_identity": signal.repository_identity,
        "pull_request_id": signal.pull_request_id,
        "pull_request_url": signal.pull_request_url,
        "title": signal.title,
        "action": signal.action,
        "source_branch": signal.source_branch,
        "target_branch": signal.target_branch,
        "head_sha": signal.head_sha,
        "merge_commit_sha": signal.merge_commit_sha,
        "status": signal.status,
        "metadata": signal.signal_metadata,
        "created_by_user_id": signal.created_by_user_id,
        "created_at": signal.created_at,
    }


def _serialize_work_item(work_item) -> dict:
    return {
        "id": work_item.id,
        "external_key": work_item.external_key,
        "title": work_item.title,
        "status": work_item.status,
        "stage": work_item.stage,
    }


def _serialize_work_item_link(link) -> dict:
    return {
        "id": link.id,
        "project_id": link.project_id,
        "work_item_id": link.work_item_id,
        "provider": link.provider,
        "external_key": link.external_key,
        "external_url": link.external_url,
        "title": link.title,
        "status": link.status,
        "metadata": link.link_metadata,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
    }


def _upsert_task_link(
    *,
    runtime: CoreRuntime,
    project,
    work_item,
    principal: Principal,
    task_provider: str | None,
    task_key: str | None,
    task_url: str | None,
    title: str | None,
    metadata: dict[str, Any],
):
    provider = (task_provider or "").strip()
    external_url = (task_url or "").strip()
    external_key = (task_key or "").strip() or _extract_task_key_from_url(external_url)
    if not provider or not external_key:
        return None
    return runtime.upsert_work_item_link(
        org_id=project.org_id,
        project_id=project.id,
        work_item_id=work_item.id,
        provider=provider,
        external_key=external_key,
        external_url=external_url or None,
        title=title,
        status="active",
        metadata=metadata,
        created_by_user_id=principal.user_id,
    )


def _extract_task_key_from_url(task_url: str) -> str | None:
    if not task_url:
        return None
    match = re.search(r"([A-Z][A-Z0-9]+-\d+)(?:\b|$)", task_url)
    if match:
        return match.group(1)
    return task_url.rstrip("/").split("/")[-1] or None


def _resolve_project(runtime: CoreRuntime, project_id: str | None, repository_identity: str):
    if project_id:
        return runtime.get_project(project_id)
    return runtime.find_project_by_git_remote(repository_identity)


def _resolve_work_item_key(
    *,
    explicit_key: str | None,
    task_url: str | None,
    source_branch: str | None,
    title: str | None,
) -> str | None:
    for candidate in [explicit_key, _extract_task_key_from_url(task_url or ""), source_branch, title]:
        if not candidate:
            continue
        match = re.search(r"([A-Z][A-Z0-9]+-\d+)", candidate)
        if match:
            return match.group(1)
    return explicit_key


def _freshness_signal_status(head_revision, observed_head_sha: str) -> str:
    if head_revision is None:
        return "missing_context"
    if head_revision.commit_sha == observed_head_sha:
        return "current_context"
    return "stale_context"


def _freshness_state(signal_status: str) -> str:
    if signal_status == "current_context":
        return "current"
    if signal_status == "stale_context":
        return "stale"
    return "missing"


def _serialize_context_freshness(state: str, branch: str, head_revision, observed_head_sha: str) -> dict:
    return {
        "state": state,
        "branch": branch,
        "head_revision_id": head_revision.id if head_revision is not None else None,
        "head_commit_sha": head_revision.commit_sha if head_revision is not None else None,
        "observed_head_sha": observed_head_sha,
    }


def _create_refresh_proposal_for_observed_head(
    *,
    runtime: CoreRuntime,
    project,
    work_item,
    principal: Principal,
    branch: str,
    repository_identity: str,
    provider: str,
    observed_head_sha: str,
    previous_head_sha: str | None,
    reason: str,
    signal_id: str,
):
    head_revision = runtime.get_head_context_revision_for_project(project_id=project.id, branch=branch)
    signal_status = _freshness_signal_status(head_revision, observed_head_sha)
    freshness_state = _freshness_state(signal_status)
    context_freshness = _serialize_context_freshness(freshness_state, branch, head_revision, observed_head_sha)
    if signal_status != "stale_context":
        return context_freshness, None
    stream = runtime.ensure_context_stream(
        org_id=project.org_id,
        project_id=project.id,
        branch=branch,
        repository_identity={"git_remotes": project.git_remotes, "observed": repository_identity},
    )
    proposal = runtime.create_context_proposal(
        org_id=project.org_id,
        project_id=project.id,
        stream_id=stream.id,
        work_item_id=work_item.id if work_item is not None else None,
        session_id=None,
        type="refresh",
        status="submitted",
        title=f"Refresh context for {branch} at {observed_head_sha}",
        summary="Repository automation indicates accepted context is behind the observed branch head.",
        content={
            "refresh_required": True,
            "reason": reason,
            "repository_identity": repository_identity,
            "branch": branch,
            "observed_head_sha": observed_head_sha,
            "previous_head_sha": previous_head_sha,
        },
        source_anchors=[],
        provenance={
            "source": reason,
            "provider": provider,
            "signal_id": signal_id,
            "schema_version": "context-revision/v1",
        },
        target_branch=branch,
        expected_head_revision_id=head_revision.id if head_revision is not None else None,
        from_commit_sha=head_revision.commit_sha if head_revision is not None else previous_head_sha,
        to_commit_sha=observed_head_sha,
        created_by_user_id=principal.user_id,
    )
    return context_freshness, proposal


def _serialize_context_proposal(proposal) -> dict:
    return {
        "id": proposal.id,
        "project_id": proposal.project_id,
        "work_item_id": proposal.work_item_id,
        "type": proposal.type,
        "status": proposal.status,
        "title": proposal.title,
        "summary": proposal.summary,
        "target_branch": proposal.target_branch,
        "expected_head_revision_id": proposal.expected_head_revision_id,
        "from_commit_sha": proposal.from_commit_sha,
        "to_commit_sha": proposal.to_commit_sha,
    }


def _revision_signal_next_actions(signal_status: str) -> list[dict]:
    if signal_status == "stale_context":
        return [
            {
                "type": "review_context_refresh_proposal",
                "reason": "Accepted project context is behind the observed repository branch head.",
            }
        ]
    if signal_status == "missing_context":
        return [
            {
                "type": "generate_initial_context",
                "reason": "No accepted context revision exists for this branch.",
            }
        ]
    return [{"type": "no_action", "reason": "Accepted context already matches the observed branch head."}]


def _pull_request_next_actions(action: str, freshness_state: str | None) -> list[dict]:
    if action == "merged" and freshness_state == "stale":
        return [
            {
                "type": "review_context_refresh_proposal",
                "reason": "Merged PR/MR advanced the target branch beyond the accepted project context.",
            }
        ]
    if action == "merged" and freshness_state == "missing":
        return [{"type": "generate_initial_context", "reason": "Merged PR/MR was observed but no accepted context exists."}]
    return [{"type": "no_action", "reason": "PR/MR signal was recorded without requiring user interruption."}]
