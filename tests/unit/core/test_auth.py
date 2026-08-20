import hashlib

import pytest
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.models import CredentialModel, ProjectMembershipModel, ProjectModel, SkillModel
from packages.core.auth import (
    BootstrapAuthError,
    bootstrap_local_identity,
    hash_token,
    token_diagnostic_prefix,
)
from packages.core.uow import SqlAlchemyUnitOfWork


def _session(database_url: str):
    engine = create_app_engine(database_url)
    return sessionmaker(bind=engine)()


def test_token_storage_uses_sha256_hash_and_non_secret_prefix(tmp_path):
    token = "human-token-secret-value"

    digest = hash_token(token)
    prefix = token_diagnostic_prefix(token)

    assert digest == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert token not in digest
    assert token not in prefix
    assert prefix == f"sha256:{digest[:8]}"
    assert not prefix.startswith(token[:8])


def test_bootstrap_creates_human_and_agent_credentials_for_same_local_user(tmp_path):
    session = _session(f"sqlite+pysqlite:///{tmp_path / 'auth.db'}")
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            project = ProjectModel(org_id="org_bootstrap", name="Existing", slug="existing")
            session.add(project)
            uow.commit()

        principal = bootstrap_local_identity(
            session,
            human_token="human-token-secret-value",
            agent_token="agent-token-secret-value",
            org_id="org_bootstrap",
        )

        credentials = session.query(CredentialModel).order_by(CredentialModel.kind).all()
        assert [credential.kind for credential in credentials] == ["agent", "human"]
        assert {credential.user_id for credential in credentials} == {principal.user_id}
        assert {credential.token_hash for credential in credentials} == {
            hash_token("human-token-secret-value"),
            hash_token("agent-token-secret-value"),
        }
        assert all("token-secret-value" not in credential.token_prefix for credential in credentials)
        memberships = session.query(ProjectMembershipModel).all()
        assert [(membership.project_id, membership.user_id) for membership in memberships] == [
            (project.id, principal.user_id)
        ]
    finally:
        session.close()


def test_bootstrap_fails_closed_when_org_is_ambiguous_without_configured_org(tmp_path):
    session = _session(f"sqlite+pysqlite:///{tmp_path / 'ambiguous.db'}")
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            session.add(ProjectModel(org_id="org_a", name="A", slug="a"))
            session.add(ProjectModel(org_id="org_b", name="B", slug="b"))
            uow.commit()

        with pytest.raises(BootstrapAuthError, match="ambiguous"):
            bootstrap_local_identity(
                session,
                human_token="human-token-secret-value",
                agent_token="agent-token-secret-value",
                org_id=None,
            )
    finally:
        session.close()


def test_bootstrap_treats_non_project_legacy_orgs_as_ambiguous(tmp_path):
    session = _session(f"sqlite+pysqlite:///{tmp_path / 'legacy-orgs.db'}")
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            session.add(SkillModel(org_id="org_a", slug="a", name="A"))
            session.add(SkillModel(org_id="org_b", slug="b", name="B"))
            uow.commit()

        with pytest.raises(BootstrapAuthError, match="ambiguous"):
            bootstrap_local_identity(
                session,
                human_token="human-token-secret-value",
                agent_token="agent-token-secret-value",
                org_id=None,
            )
    finally:
        session.close()
