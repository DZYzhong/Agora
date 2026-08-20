from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

from sqlalchemy.orm import Session

from packages.core.models import CredentialModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.uow import SqlAlchemyUnitOfWork

LOCAL_BOOTSTRAP_ORG_ID = "local-org"


class BootstrapAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class Principal:
    org_id: str
    user_id: str
    credential_id: str
    credential_kind: str
    token_prefix: str
    is_bypass: bool = False

    @property
    def is_human(self) -> bool:
        return self.is_bypass or self.credential_kind == "human"

    @property
    def is_agent(self) -> bool:
        return self.credential_kind == "agent"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_diagnostic_prefix(token: str) -> str:
    return f"{token[:8]}..."


def bypass_principal() -> Principal:
    return Principal(
        org_id="",
        user_id="auth-bypass-user",
        credential_id="auth-bypass-credential",
        credential_kind="human",
        token_prefix="bypass...",
        is_bypass=True,
    )


def bootstrap_local_identity(
    session: Session,
    *,
    human_token: str | None,
    agent_token: str | None,
    org_id: str | None,
) -> Principal:
    if not human_token or not agent_token:
        raise BootstrapAuthError("AGORA_BOOTSTRAP_HUMAN_TOKEN and AGORA_BOOTSTRAP_AGENT_TOKEN are required")
    if human_token == agent_token:
        raise BootstrapAuthError("bootstrap human and agent tokens must be different")

    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        resolved_org_id = org_id or _resolve_bootstrap_org_id(repo.list_project_org_ids())
        user = repo.get_bootstrap_user(resolved_org_id) or repo.create_bootstrap_user(resolved_org_id)
        human = repo.upsert_credential(
            user_id=user.id,
            kind="human",
            token_hash=hash_token(human_token),
            token_prefix=token_diagnostic_prefix(human_token),
        )
        repo.upsert_credential(
            user_id=user.id,
            kind="agent",
            token_hash=hash_token(agent_token),
            token_prefix=token_diagnostic_prefix(agent_token),
        )
        repo.grant_user_to_org_projects(org_id=resolved_org_id, user_id=user.id)
        principal = _principal_from_credential(repo, human)
        uow.commit()
    return principal


def resolve_principal(session: Session, *, bearer_token: str) -> Principal | None:
    repo = IdentityRepository(session)
    credential = repo.get_credential_by_hash(hash_token(bearer_token))
    if credential is None:
        return None
    user = repo.get_user(credential.user_id)
    if user is None or user.status != "active":
        return None
    repo.touch_credential(credential, at=datetime.now(timezone.utc))
    return Principal(
        org_id=user.org_id,
        user_id=user.id,
        credential_id=credential.id,
        credential_kind=credential.kind,
        token_prefix=credential.token_prefix,
    )


def has_project_membership(session: Session, *, principal: Principal, project_id: str) -> bool:
    if principal.is_bypass:
        return True
    return IdentityRepository(session).has_project_membership(project_id=project_id, user_id=principal.user_id)


def _resolve_bootstrap_org_id(existing_org_ids: list[str]) -> str:
    if not existing_org_ids:
        return LOCAL_BOOTSTRAP_ORG_ID
    if len(existing_org_ids) == 1:
        return existing_org_ids[0]
    raise BootstrapAuthError("AGORA_BOOTSTRAP_ORG_ID is required because existing organizations are ambiguous")


def _principal_from_credential(repo: IdentityRepository, credential: CredentialModel) -> Principal:
    user = repo.get_user(credential.user_id)
    if user is None:
        raise BootstrapAuthError("bootstrap credential does not reference an active user")
    return Principal(
        org_id=user.org_id,
        user_id=user.id,
        credential_id=credential.id,
        credential_kind=credential.kind,
        token_prefix=credential.token_prefix,
    )
