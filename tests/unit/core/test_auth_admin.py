import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.core.auth import Principal, hash_token
from packages.core.database import Base
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.security import SecurityRepository
from packages.core.auth_admin import (
    AdminActionError,
    activate_user,
    bootstrap_admin,
    create_user_with_activation,
    issue_reset_credential,
    reset_password,
    revoke_credential,
    set_user_enabled,
)


@pytest.fixture
def session_factory():
    # One isolated in-memory database per test. expire_on_commit=False keeps
    # returned ORM instances usable after the unit-of-work session is released.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _admin_principal(session_factory, *, org_id="org_1") -> Principal:
    user = bootstrap_admin(
        session_factory(),
        org_id=org_id,
        admin_username="root",
        admin_password="root-password",
        display_name="Root",
    )
    return Principal(
        org_id=org_id,
        user_id=user.id,
        credential_id="cred-admin",
        credential_kind="human",
        token_prefix="sha256:admin",
    )


def test_bootstrap_admin_creates_org_admin_with_argon2id_hash(session_factory):
    user = bootstrap_admin(session_factory(), org_id="org_boot", admin_username="root", admin_password="s3cret!")

    assert user.username == "root"
    assert user.status == "active"
    assert user.password_hash.startswith("$argon2id$")
    assert "s3cret!" not in user.password_hash

    memberships = IdentityRepository(session_factory()).list_org_admins("org_boot")
    assert [member.id for member in memberships] == [user.id]


def test_bootstrap_admin_is_one_time(session_factory):
    bootstrap_admin(session_factory(), org_id="org_one", admin_username="root", admin_password="pw")

    with pytest.raises(AdminActionError) as exc_info:
        bootstrap_admin(session_factory(), org_id="org_one", admin_username="root2", admin_password="pw2")
    assert exc_info.value.code == "ADMIN_ALREADY_BOOTSTRAPPED"


def test_bootstrap_admin_writes_audit_event(session_factory):
    user = bootstrap_admin(session_factory(), org_id="org_audit", admin_username="root", admin_password="pw")

    events = SecurityRepository(session_factory()).list_by_org("org_audit")
    assert any(
        event.action == "admin.bootstrap"
        and event.target_type == "organization"
        and event.target_id == "org_audit"
        and event.decision == "allow"
        for event in events
    )
    assert events[0].actor_user_id == user.id


def test_create_user_with_activation_returns_single_use_token(session_factory):
    admin = _admin_principal(session_factory)

    created = create_user_with_activation(
        session_factory(),
        actor=admin,
        org_id="org_1",
        username="alice",
        display_name="Alice",
    )

    assert created.activation_token
    assert created.status == "pending_activation"
    repo = IdentityRepository(session_factory())
    user = repo.get_user(created.user_id)
    assert user.password_hash is None
    credentials = repo.list_credentials_by_user(user.id)
    assert len(credentials) == 1
    assert credentials[0].kind == "activation"
    assert credentials[0].single_use is True
    assert credentials[0].expires_at is not None
    # only the hash is stored
    assert hash_token(created.activation_token) == credentials[0].token_hash
    assert created.activation_token not in credentials[0].token_hash


def test_create_user_requires_org_admin(session_factory):
    non_admin = Principal(
        org_id="org_1",
        user_id="u-other",
        credential_id="c-other",
        credential_kind="human",
        token_prefix="sha256:x",
    )

    with pytest.raises(AdminActionError) as exc_info:
        create_user_with_activation(
            session_factory(),
            actor=non_admin,
            org_id="org_1",
            username="bob",
            display_name="Bob",
        )
    assert exc_info.value.code == "ORG_ADMIN_REQUIRED"


def test_create_user_rejects_duplicate_username(session_factory):
    admin = _admin_principal(session_factory)
    create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="carol", display_name="Carol")

    with pytest.raises(AdminActionError) as exc_info:
        create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="carol", display_name="Carol2")
    assert exc_info.value.code == "USERNAME_TAKEN"


def test_activate_user_sets_password_and_consumes_token(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="dave", display_name="Dave")

    user = activate_user(session_factory(), activation_token=created.activation_token, new_password="new-password")

    assert user.status == "active"
    assert user.password_hash.startswith("$argon2id$")
    credentials = IdentityRepository(session_factory()).list_credentials_by_user(user.id)
    assert credentials[0].status == "consumed"
    assert credentials[0].consumed_at is not None


def test_activate_user_token_is_single_use(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="erin", display_name="Erin")

    activate_user(session_factory(), activation_token=created.activation_token, new_password="first")

    with pytest.raises(AdminActionError) as exc_info:
        activate_user(session_factory(), activation_token=created.activation_token, new_password="second")
    assert exc_info.value.code == "ACTIVATION_TOKEN_INVALID"


def test_activate_user_rejects_bogus_token(session_factory):
    with pytest.raises(AdminActionError) as exc_info:
        activate_user(session_factory(), activation_token="not-a-real-token", new_password="pw")
    assert exc_info.value.code == "ACTIVATION_TOKEN_INVALID"


def test_reset_flow_issues_single_use_expiring_credential(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="frank", display_name="Frank")
    activate_user(session_factory(), activation_token=created.activation_token, new_password="original")

    reset = issue_reset_credential(session_factory(), actor=admin, user_id=created.user_id)

    assert reset.reset_token
    user = reset_password(session_factory(), reset_token=reset.reset_token, new_password="rotated")
    assert user.password_hash.startswith("$argon2id$")

    with pytest.raises(AdminActionError) as exc_info:
        reset_password(session_factory(), reset_token=reset.reset_token, new_password="again")
    assert exc_info.value.code == "RESET_TOKEN_INVALID"


def test_disable_user_revokes_credentials_and_blocks_reactivation_with_old_token(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="grace", display_name="Grace")

    user = set_user_enabled(session_factory(), actor=admin, user_id=created.user_id, enabled=False)

    assert user.status == "disabled"
    credentials = IdentityRepository(session_factory()).list_credentials_by_user(created.user_id)
    assert credentials[0].status == "revoked"

    # old activation token is now unusable
    with pytest.raises(AdminActionError):
        activate_user(session_factory(), activation_token=created.activation_token, new_password="pw")

    # enable again works
    set_user_enabled(session_factory(), actor=admin, user_id=created.user_id, enabled=True)
    assert IdentityRepository(session_factory()).get_user(created.user_id).status == "active"


def test_revoke_credential_marks_inactive(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="heidi", display_name="Heidi")
    credential = IdentityRepository(session_factory()).list_credentials_by_user(created.user_id)[0]

    revoked = revoke_credential(session_factory(), actor=admin, credential_id=credential.id)

    assert revoked.status == "revoked"
    assert IdentityRepository(session_factory()).get_credential_by_hash(credential.token_hash) is None


def test_identity_actions_are_audited(session_factory):
    admin = _admin_principal(session_factory)
    created = create_user_with_activation(session_factory(), actor=admin, org_id="org_1", username="ivan", display_name="Ivan")
    activate_user(session_factory(), activation_token=created.activation_token, new_password="pw")

    actions = {event.action for event in SecurityRepository(session_factory()).list_by_org("org_1")}
    assert {"admin.bootstrap", "user.create", "user.activate"} <= actions
