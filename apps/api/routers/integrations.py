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
            "evidence": _serialize_quality_evidence(evidence),
            "project_status": project_status.__dict__,
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
