"""PR3 B1: organization and project membership management API tests."""

from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.auth import Principal
from packages.core.models import ProjectModel, UserModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.security import SecurityRepository
from packages.core.services.membership import MembershipError, add_org_member, remove_org_member, set_org_member_role
from packages.core.uow import SqlAlchemyUnitOfWork

ORG = "membership-org"


def _client() -> TestClient:
    return TestClient(app)


def _create_user(client: TestClient, username: str, display_name: str, org_id: str = ORG) -> dict:
    created = client.post(
        "/users",
        json={"org_id": org_id, "username": username, "display_name": display_name},
    ).json()
    activated = client.post(
        "/users/activate",
        json={"activation_token": created["activation_token"], "new_password": f"{username}-password-1"},
    )
    assert activated.status_code == 200
    return activated.json()["user"]


def _create_project(client: TestClient, slug: str, org_id: str = ORG) -> dict:
    response = client.post(
        "/projects",
        json={"org_id": org_id, "name": slug.replace("-", " ").title(), "slug": slug},
    )
    assert response.status_code == 201
    return response.json()


# --- organization membership ------------------------------------------------


def test_org_member_add_list_role_and_remove():
    client = _client()
    alice = _create_user(client, "alice", "Alice")
    bob = _create_user(client, "bob", "Bob")

    added = client.post(
        f"/organizations/{ORG}/members",
        json={"username": "alice", "role": "member"},
    )
    assert added.status_code == 201
    assert added.json()["user"]["id"] == alice["id"]
    assert added.json()["role"] == "member"

    # Adding again updates the role (audited as role change, not duplicate row).
    promoted = client.post(
        f"/organizations/{ORG}/members",
        json={"user_id": alice["id"], "role": "admin"},
    )
    assert promoted.status_code == 201
    assert promoted.json()["role"] == "admin"

    listed = client.get(f"/organizations/{ORG}/members").json()
    usernames = {member["user"]["username"]: member["role"] for member in listed}
    assert usernames["alice"] == "admin"
    assert "bob" not in usernames

    changed = client.patch(f"/organizations/{ORG}/members/{alice['id']}", json={"role": "member"})
    assert changed.status_code == 200
    assert changed.json()["role"] == "member"

    removed = client.delete(f"/organizations/{ORG}/members/{alice['id']}")
    assert removed.status_code == 204
    # Removing a non-member is a stable 400.
    again = client.delete(f"/organizations/{ORG}/members/{alice['id']}")
    assert again.status_code == 400
    assert again.json()["detail"]["code"] == "NOT_ORG_MEMBER"

    # Audit trail exists for every membership mutation.
    from apps.api.dependencies import get_engine
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    db = sessionmaker(bind=engine)()
    try:
        actions = {
            event.action
            for event in SecurityRepository(db).list_by_org(ORG)
        }
        assert {"org.member.add", "org.member.role", "org.member.remove"} <= actions
    finally:
        db.close()


def test_org_member_add_rejects_bad_input():
    client = _client()
    _create_user(client, "carol", "Carol")

    invalid_role = client.post(
        f"/organizations/{ORG}/members",
        json={"username": "carol", "role": "superuser"},
    )
    assert invalid_role.status_code == 400
    assert invalid_role.json()["detail"]["code"] == "ROLE_NOT_ALLOWED"

    both_ids = client.post(
        f"/organizations/{ORG}/members",
        json={"user_id": "x", "username": "carol", "role": "member"},
    )
    assert both_ids.status_code == 400
    assert both_ids.json()["detail"]["code"] == "IDENTIFIER_REQUIRED"

    neither = client.post(
        f"/organizations/{ORG}/members",
        json={"role": "member"},
    )
    assert neither.status_code == 400

    unknown = client.post(
        f"/organizations/{ORG}/members",
        json={"username": "ghost", "role": "member"},
    )
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "USER_NOT_FOUND"


# --- project membership -----------------------------------------------------


def test_project_member_add_list_role_and_remove():
    client = _client()
    _create_user(client, "dev", "Dev")
    _create_user(client, "reviewer", "Reviewer")
    project = _create_project(client, "membership-project")

    added = client.post(
        f"/projects/{project['id']}/members",
        json={"username": "dev", "role": "developer"},
    )
    assert added.status_code == 201
    assert added.json()["role"] == "developer"

    reviewed = client.post(
        f"/projects/{project['id']}/members",
        json={"username": "reviewer", "role": "reviewer"},
    )
    assert reviewed.status_code == 201

    listed = client.get(f"/projects/{project['id']}/members").json()
    roles = {m["user"]["username"]: m["role"] for m in listed}
    assert roles["dev"] == "developer"
    assert roles["reviewer"] == "reviewer"

    demoted = client.patch(
        f"/projects/{project['id']}/members/{added.json()['user']['id']}",
        json={"role": "viewer"},
    )
    assert demoted.status_code == 200
    assert demoted.json()["role"] == "viewer"

    removed = client.delete(
        f"/projects/{project['id']}/members/{added.json()['user']['id']}"
    )
    assert removed.status_code == 204


# --- service-layer guards (non-bypass principals) ---------------------------


def test_membership_guards_enforce_admin_and_last_admin_rules():
    from apps.api.dependencies import get_engine
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    session = sessionmaker(bind=engine)()
    org_id = "guard-org"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            repo = IdentityRepository(session)
            admin_user = repo.create_user(org_id=org_id, username="guard-admin", display_name="Guard Admin", status="active")
            member_user = repo.create_user(org_id=org_id, username="guard-member", display_name="Guard Member", status="active")
            # Capture ids before commit: post-commit attribute access would
            # trigger an autobegin on the expired ORM instance.
            admin_id = admin_user.id
            member_id = member_user.id
            repo.create_org_membership(org_id=org_id, user_id=admin_id, role="admin")
            repo.create_org_membership(org_id=org_id, user_id=member_id, role="member")
            uow.commit()

        admin_principal = Principal(
            org_id=org_id,
            user_id=admin_id,
            credential_id="c-admin",
            credential_kind="human",
            token_prefix="x",
        )
        member_principal = Principal(
            org_id=org_id,
            user_id=member_id,
            credential_id="c-member",
            credential_kind="human",
            token_prefix="x",
        )

        # A plain member cannot manage org membership.
        try:
            add_org_member(session, actor=member_principal, org_id=org_id, role="member", username="guard-admin")
            raise AssertionError("expected ORG_ADMIN_REQUIRED")
        except MembershipError as exc:
            assert exc.code == "ORG_ADMIN_REQUIRED"

        # Owner role is reserved for the owner.
        try:
            add_org_member(session, actor=admin_principal, org_id=org_id, role="owner", username="guard-admin")
            raise AssertionError("expected OWNER_ROLE_RESERVED")
        except MembershipError as exc:
            assert exc.code == "OWNER_ROLE_RESERVED"

        # A sole org admin cannot demote themselves (lockout guard).
        try:
            set_org_member_role(session, actor=admin_principal, org_id=org_id, user_id=admin_id, role="member")
            raise AssertionError("expected LAST_ADMIN_GUARD")
        except MembershipError as exc:
            assert exc.code == "LAST_ADMIN_GUARD"

        # Removing the sole admin is also blocked.
        try:
            remove_org_member(session, actor=admin_principal, org_id=org_id, user_id=admin_id)
            raise AssertionError("expected LAST_ADMIN_GUARD")
        except MembershipError as exc:
            assert exc.code == "LAST_ADMIN_GUARD"
    finally:
        session.rollback()
        session.close()
