from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.auth_session import SESSION_COOKIE_NAME, resolve_session_principal
from apps.api.dependencies import get_db_session
from packages.core.services.approval_grants import (
    APPROVAL_POLICY_VERSION,
    ApprovalDeniedError,
    is_reauth_valid,
    issue_approval_grant,
)
from packages.core.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/approval-grants", tags=["approvals"])


class IssueApprovalGrantRequest(BaseModel):
    object_type: str
    object_id: str
    payload_digest: str
    decision: str
    policy_version: str = APPROVAL_POLICY_VERSION


@router.post("", status_code=201)
def issue_grant(
    payload: IssueApprovalGrantRequest,
    request: Request,
    session: Session = Depends(get_db_session),
):
    """Issue a bound, short-lived, single-use approval grant from a reauthenticated Web human session."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    with SqlAlchemyUnitOfWork(session) as uow:
        principal = resolve_session_principal(session, session_token=token)
        if principal is None:
            raise HTTPException(status_code=401, detail={"code": "SESSION_REQUIRED", "message": "No active session"})
        if not is_reauth_valid(session, principal):
            raise HTTPException(
                status_code=403,
                detail={"code": "REAUTH_REQUIRED", "message": "Reauthentication required to issue an approval grant"},
            )
        try:
            grant = issue_approval_grant(
                session,
                actor=principal,
                org_id=principal.org_id,
                object_type=payload.object_type,
                object_id=payload.object_id,
                payload_digest=payload.payload_digest,
                decision=payload.decision,
                policy_version=payload.policy_version,
            )
        except ApprovalDeniedError as exc:
            raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message}) from exc
        uow.commit()
    return {
        "grant_id": grant.id,
        "object_type": grant.object_type,
        "object_id": grant.object_id,
        "decision": grant.decision,
        "policy_version": grant.policy_version,
        "expires_at": grant.expires_at,
        "single_use": True,
    }
