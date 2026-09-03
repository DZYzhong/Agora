from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.core.models import (
    AssetModel,
    ContextPackModel,
    CredentialModel,
    OrganizationMembershipModel,
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

    def get_credential(self, credential_id: str) -> CredentialModel | None:
        return self.session.get(CredentialModel, credential_id)

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

    # --- PR1B user lifecycle -------------------------------------------------

    def get_user_by_username(self, *, org_id: str, username: str) -> UserModel | None:
        statement = select(UserModel).where(
            UserModel.org_id == org_id,
            UserModel.username == username,
        )
        return self.session.scalars(statement).first()

    def create_user(
        self,
        *,
        org_id: str,
        username: str,
        display_name: str,
        password_hash: str | None = None,
        status: str = "active",
    ) -> UserModel:
        user = UserModel(
            org_id=org_id,
            username=username,
            display_name=display_name,
            password_hash=password_hash,
            status=status,
            is_placeholder=False,
        )
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValueError(f"Username already exists: {username}") from exc
        self.session.refresh(user)
        return user

    def list_users(self, org_id: str) -> list[UserModel]:
        statement = (
            select(UserModel)
            .where(UserModel.org_id == org_id)
            .order_by(UserModel.created_at.asc(), UserModel.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def set_user_password(self, user: UserModel, *, password_hash: str) -> None:
        user.password_hash = password_hash
        self.session.flush()

    def set_user_status(self, user: UserModel, *, status: str) -> None:
        user.status = status
        self.session.flush()

    def create_single_use_credential(
        self,
        *,
        user_id: str,
        kind: str,
        token_hash: str,
        token_prefix: str,
        expires_at: datetime,
    ) -> CredentialModel:
        credential = CredentialModel(
            user_id=user_id,
            kind=kind,
            token_hash=token_hash,
            token_prefix=token_prefix,
            status="active",
            expires_at=expires_at,
            single_use=True,
        )
        self.session.add(credential)
        self.session.flush()
        self.session.refresh(credential)
        return credential

    def create_api_credential(
        self,
        *,
        user_id: str,
        kind: str,
        token_hash: str,
        token_prefix: str,
        label: str | None = None,
        expires_at: datetime | None = None,
    ) -> CredentialModel:
        credential = CredentialModel(
            user_id=user_id,
            kind=kind,
            label=label,
            token_hash=token_hash,
            token_prefix=token_prefix,
            status="active",
            expires_at=expires_at,
            single_use=False,
        )
        self.session.add(credential)
        self.session.flush()
        self.session.refresh(credential)
        return credential

    def get_active_single_use_credential_by_hash(
        self, token_hash: str, *, now: datetime
    ) -> CredentialModel | None:
        statement = select(CredentialModel).where(
            CredentialModel.token_hash == token_hash,
            CredentialModel.status == "active",
            CredentialModel.single_use.is_(True),
        )
        credential = self.session.scalars(statement).first()
        if credential is None:
            return None
        if credential.expires_at is not None and _expired(credential.expires_at, now=now):
            credential.status = "expired"
            self.session.flush()
            return None
        return credential

    def consume_single_use_credential(self, credential: CredentialModel, *, at: datetime) -> None:
        credential.status = "consumed"
        credential.consumed_at = at
        self.session.flush()

    def revoke_credential(self, credential: CredentialModel) -> None:
        credential.status = "revoked"
        self.session.flush()

    def revoke_user_credentials(self, user_id: str, *, kinds: tuple[str, ...] | None = None) -> int:
        statement = select(CredentialModel).where(
            CredentialModel.user_id == user_id,
            CredentialModel.status == "active",
        )
        if kinds is not None:
            statement = statement.where(CredentialModel.kind.in_(kinds))
        credentials = list(self.session.scalars(statement).all())
        for credential in credentials:
            credential.status = "revoked"
        self.session.flush()
        return len(credentials)

    def list_credentials_by_user(self, user_id: str) -> list[CredentialModel]:
        statement = (
            select(CredentialModel)
            .where(CredentialModel.user_id == user_id)
            .order_by(CredentialModel.created_at.asc(), CredentialModel.id.asc())
        )
        return list(self.session.scalars(statement).all())

    # --- organization membership ---------------------------------------------

    def create_org_membership(self, *, org_id: str, user_id: str, role: str = "member") -> OrganizationMembershipModel:
        membership = OrganizationMembershipModel(org_id=org_id, user_id=user_id, role=role)
        self.session.add(membership)
        self.session.flush()
        self.session.refresh(membership)
        return membership

    def get_org_membership(self, *, org_id: str, user_id: str) -> OrganizationMembershipModel | None:
        statement = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.org_id == org_id,
            OrganizationMembershipModel.user_id == user_id,
        )
        return self.session.scalars(statement).first()

    def list_org_admins(self, org_id: str) -> list[UserModel]:
        statement = (
            select(UserModel)
            .join(
                OrganizationMembershipModel,
                OrganizationMembershipModel.user_id == UserModel.id,
            )
            .where(
                OrganizationMembershipModel.org_id == org_id,
                OrganizationMembershipModel.role.in_(("owner", "admin")),
            )
        )
        return list(self.session.scalars(statement).all())

    # --- PR3 membership management ------------------------------------------

    def list_org_members(self, org_id: str) -> list[tuple[UserModel, OrganizationMembershipModel]]:
        statement = (
            select(UserModel, OrganizationMembershipModel)
            .join(
                OrganizationMembershipModel,
                OrganizationMembershipModel.user_id == UserModel.id,
            )
            .where(OrganizationMembershipModel.org_id == org_id)
            .order_by(UserModel.username.asc())
        )
        return list(self.session.execute(statement).all())

    def set_org_role(self, *, org_id: str, user_id: str, role: str) -> OrganizationMembershipModel:
        membership = self.get_org_membership(org_id=org_id, user_id=user_id)
        if membership is None:
            return self.create_org_membership(org_id=org_id, user_id=user_id, role=role)
        membership.role = role
        self.session.flush()
        self.session.refresh(membership)
        return membership

    def remove_org_membership(self, *, org_id: str, user_id: str) -> bool:
        membership = self.get_org_membership(org_id=org_id, user_id=user_id)
        if membership is None:
            return False
        self.session.delete(membership)
        self.session.flush()
        return True

    def count_org_administrators(self, org_id: str) -> int:
        return len(self.list_org_admins(org_id))

    def list_project_members(self, project_id: str) -> list[tuple[UserModel, ProjectMembershipModel]]:
        statement = (
            select(UserModel, ProjectMembershipModel)
            .join(
                ProjectMembershipModel,
                ProjectMembershipModel.user_id == UserModel.id,
            )
            .where(ProjectMembershipModel.project_id == project_id)
            .order_by(UserModel.username.asc())
        )
        return list(self.session.execute(statement).all())

    def remove_project_membership(self, *, project_id: str, user_id: str) -> bool:
        membership = self.get_membership(project_id=project_id, user_id=user_id)
        if membership is None:
            return False
        self.session.delete(membership)
        self.session.flush()
        return True

    def count_project_managers(self, project_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(ProjectMembershipModel)
            .where(
                ProjectMembershipModel.project_id == project_id,
                ProjectMembershipModel.role.in_(("owner", "admin")),
            )
        )
        return int(self.session.scalar(statement) or 0)


def _expired(expires_at: datetime, *, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        return expires_at <= now.replace(tzinfo=None)
    return expires_at <= now
