from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import (
    AssetModel,
    ContextPackModel,
    CredentialModel,
    ProjectInitializationJobModel,
    ProjectMembershipModel,
    ProjectModel,
    SkillModel,
    SkillRunModel,
    TaskSessionModel,
    UserModel,
    WritebackModel,
)


class IdentityRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_project_org_ids(self) -> list[str]:
        org_ids: set[str] = set()
        for model in (
            ProjectModel,
            AssetModel,
            ProjectInitializationJobModel,
            ContextPackModel,
            SkillModel,
            SkillRunModel,
            TaskSessionModel,
            WritebackModel,
        ):
            statement = select(model.org_id).distinct().where(model.org_id.is_not(None))
            org_ids.update(org_id for org_id in self.session.scalars(statement).all() if org_id)
        return sorted(org_ids)

    def get_bootstrap_user(self, org_id: str) -> UserModel | None:
        statement = select(UserModel).where(
            UserModel.org_id == org_id,
            UserModel.display_name == "Local Bootstrap User",
            UserModel.is_placeholder.is_(False),
        )
        return self.session.scalars(statement).first()

    def create_bootstrap_user(self, org_id: str) -> UserModel:
        user = UserModel(org_id=org_id, display_name="Local Bootstrap User", status="active", is_placeholder=False)
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user

    def upsert_credential(
        self,
        *,
        user_id: str,
        kind: str,
        token_hash: str,
        token_prefix: str,
    ) -> CredentialModel:
        credential = self.get_credential_by_hash(token_hash)
        if credential is None:
            statement = select(CredentialModel).where(CredentialModel.user_id == user_id, CredentialModel.kind == kind)
            credential = self.session.scalars(statement).first()
        if credential is None:
            credential = CredentialModel(
                user_id=user_id,
                kind=kind,
                token_hash=token_hash,
                token_prefix=token_prefix,
                status="active",
            )
            self.session.add(credential)
        else:
            credential.user_id = user_id
            credential.kind = kind
            credential.token_hash = token_hash
            credential.token_prefix = token_prefix
            credential.status = "active"
        self.session.flush()
        self.session.refresh(credential)
        return credential

    def get_credential_by_hash(self, token_hash: str) -> CredentialModel | None:
        statement = select(CredentialModel).where(
            CredentialModel.token_hash == token_hash,
            CredentialModel.status == "active",
        )
        return self.session.scalars(statement).first()

    def get_user(self, user_id: str) -> UserModel | None:
        return self.session.get(UserModel, user_id)

    def grant_membership(self, *, project_id: str, user_id: str, role: str = "member") -> ProjectMembershipModel:
        membership = self.get_membership(project_id=project_id, user_id=user_id)
        if membership is None:
            membership = ProjectMembershipModel(project_id=project_id, user_id=user_id, role=role)
            self.session.add(membership)
        else:
            membership.role = role
        self.session.flush()
        self.session.refresh(membership)
        return membership

    def grant_user_to_org_projects(self, *, org_id: str, user_id: str) -> None:
        statement = select(ProjectModel.id).where(ProjectModel.org_id == org_id)
        for project_id in self.session.scalars(statement).all():
            self.grant_membership(project_id=project_id, user_id=user_id)

    def get_membership(self, *, project_id: str, user_id: str) -> ProjectMembershipModel | None:
        statement = select(ProjectMembershipModel).where(
            ProjectMembershipModel.project_id == project_id,
            ProjectMembershipModel.user_id == user_id,
        )
        return self.session.scalars(statement).first()

    def has_project_membership(self, *, project_id: str, user_id: str) -> bool:
        return self.get_membership(project_id=project_id, user_id=user_id) is not None

    def touch_credential(self, credential: CredentialModel, *, at: datetime) -> None:
        credential.last_used_at = at
        self.session.flush()
