"""PR3 B5: principal × action RBAC matrix (service/guard level).

Enumerates, for the PR3 surfaces (membership and credential management), the
allowed/denied outcome of every actor role on representative actions. Runs
against an isolated in-memory schema; guards are exercised directly so the
matrix is deterministic and fast. Approval-denial matrix (agent/ci/personal
cannot approve) is covered by tests/integration/api/test_approval_grants.py.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.core.database import Base
from packages.core.auth import Principal
from packages.core.models import ProjectModel, UserModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.services.credentials import (
    CredentialError,
    issue_api_credential,
)
from packages.core.services.membership import (
    MembershipError,
    add_org_member,
    add_project_member,
    remove_org_member,
    set_org_member_role,
    set_project_member_role,
)

ORG = "rbac-org"
OTHER_ORG = "rbac-other"

# actor kind -> (org membership role, project role on the shared project,
# credential kind for the principal)
ACTOR_ROLES = {
    "org_owner": ("owner", "owner", "human"),
    "org_admin": ("admin", "member", "human"),
    "org_member": ("member", "member", "human"),
    "pj_owner": ("member", "owner", "human"),
    "pj_admin": ("member", "admin", "human"),
    "pj_reviewer": ("member", "reviewer", "human"),
    "pj_pm": ("member", "pm", "human"),
    "pj_quality": ("member", "quality", "human"),
    "pj_dev": ("member", "developer", "human"),
    "pj_viewer": ("member", "viewer", "human"),
    "pj_nonmember": ("member", None, "human"),
    "agent_of_admin": ("admin", "member", "agent"),
    "ci_of_admin": ("admin", "member", "ci"),
}


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _user(session: Session, username: str, org_id: str) -> UserModel:
    repo = IdentityRepository(session)
    user = repo.create_user(org_id=org_id, username=username, display_name=username, status="active")
    repo.create_org_membership(org_id=org_id, user_id=user.id, role="member")
    return user


def build_scenario(session: Session, actor_kind: str):
    """Build the shared org/project/users and return a context dict."""
    org_role, project_role, credential_kind = ACTOR_ROLES[actor_kind]
    repo = IdentityRepository(session)
    project_repo = ProjectRepository(session)

    actor = repo.create_user(org_id=ORG, username=f"actor-{actor_kind}", display_name="Actor", status="active")
    if org_role:
        repo.create_org_membership(org_id=ORG, user_id=actor.id, role=org_role)
    victim = _user(session, "victim", ORG)
    other = _user(session, "outsider", OTHER_ORG)
    second_admin = _user(session, "second-admin", ORG)
    repo.set_org_role(org_id=ORG, user_id=second_admin.id, role="admin")

    project = project_repo.create(org_id=ORG, name="RBAC Project", slug="rbac-project")
    repo.grant_membership(project_id=project.id, user_id=victim.id, role="member")
    if project_role:
        repo.grant_membership(project_id=project.id, user_id=actor.id, role=project_role)
    # A separate project owner seat for owner-management rows.
    owner = repo.create_user(org_id=ORG, username="pj-owner", display_name="PJ Owner", status="active")
    repo.grant_membership(project_id=project.id, user_id=owner.id, role="owner")

    principal = Principal(
        org_id=ORG,
        user_id=actor.id,
        credential_id=f"cred-{actor_kind}",
        credential_kind=credential_kind,
        token_prefix="matrix",
    )
    return {
        "principal": principal,
        "project_id": project.id,
        "victim_id": victim.id,
        "other_id": other.id,
        "admin_id": second_admin.id,
    }


def expect(action, session, principal, *args, **kwargs):
    try:
        action(session, principal=principal, *args, **kwargs)
        return None
    except (MembershipError, CredentialError) as exc:
        return exc.code


# action factories ------------------------------------------------------------

def org_add(session, *, principal, target_id):
    return add_org_member(session, actor=principal, org_id=ORG, role="member", user_id=target_id)


def org_add_owner(session, *, principal, target_id):
    return add_org_member(session, actor=principal, org_id=ORG, role="owner", user_id=target_id)


def org_remove_admin(session, *, principal, target_id):
    return remove_org_member(session, actor=principal, org_id=ORG, user_id=target_id)


def proj_add_dev(session, *, principal, project_id, target_id):
    return add_project_member(
        session, actor=principal, project_id=project_id, role="developer", user_id=target_id
    )


def proj_add_owner(session, *, principal, project_id, target_id):
    return add_project_member(
        session, actor=principal, project_id=project_id, role="owner", user_id=target_id
    )


def proj_set_owner(session, *, principal, project_id, target_id):
    return set_project_member_role(
        session, actor=principal, project_id=project_id, user_id=target_id, role="owner"
    )


def cred_issue(session, *, principal, target_id):
    return issue_api_credential(
        session, actor=principal, user_id=target_id, kind="agent", label="matrix"
    )


# matrix rows: (label, action, actor kinds -> expected outcome)
# expected: None = allowed; string = denied with that code.
MATRIX = [
    # --- organization membership management: org admin required, human only --
    ("org.add", org_add, {
        "org_owner": None, "org_admin": None,
        "org_member": "ORG_ADMIN_REQUIRED",
        "pj_owner": "ORG_ADMIN_REQUIRED",  # project ownership grants nothing at org level
        "pj_admin": "ORG_ADMIN_REQUIRED",
        "pj_nonmember": "ORG_ADMIN_REQUIRED",
        "agent_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
        "ci_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
    }),
    ("org.add.owner (owner only)", org_add_owner, {
        "org_owner": None,
        "org_admin": "OWNER_ROLE_RESERVED",
        "pj_owner": "ORG_ADMIN_REQUIRED",
    }),
    ("org.remove.admin (owner only)", org_remove_admin, {
        "org_owner": None,
        "org_admin": "ORG_ADMIN_REQUIRED",
    }),
    ("org.set.role by admin on member", lambda session, principal, target_id: set_org_member_role(
        session, actor=principal, org_id=ORG, user_id=target_id, role="member"
    ), {
        "org_admin": None, "org_member": "ORG_ADMIN_REQUIRED",
    }),
    # --- project membership management ---------------------------------------
    ("proj.add.developer", proj_add_dev, {
        "org_owner": None, "org_admin": None,
        "pj_owner": None, "pj_admin": None,
        "pj_reviewer": "PROJECT_MANAGER_REQUIRED",
        "pj_pm": "PROJECT_MANAGER_REQUIRED",
        "pj_quality": "PROJECT_MANAGER_REQUIRED",
        "pj_dev": "PROJECT_MANAGER_REQUIRED",
        "pj_viewer": "PROJECT_MANAGER_REQUIRED",
        "pj_nonmember": "PROJECT_MANAGER_REQUIRED",
        "agent_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
        "ci_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
    }),
    ("proj.add.owner (owner/org-admin only)", proj_add_owner, {
        "pj_owner": None, "org_admin": None,
        "pj_admin": "OWNER_ROLE_RESERVED",
        "org_owner": None,
    }),
    ("proj.set.owner (owner/org-admin only)", proj_set_owner, {
        "pj_owner": None, "org_admin": None,
        "pj_admin": "OWNER_ROLE_RESERVED",
    }),
    # --- credential issuance: org admin required, human only ----------------
    ("cred.issue", cred_issue, {
        "org_owner": None, "org_admin": None,
        "org_member": "ORG_ADMIN_REQUIRED",
        "pj_owner": "ORG_ADMIN_REQUIRED",
        "agent_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
        "ci_of_admin": "HUMAN_CREDENTIAL_REQUIRED",
    }),
    # Org admin of one org cannot issue credentials for a user in another org.
    ("cred.issue.cross-org", cred_issue, {
        "org_admin": "ORG_ADMIN_REQUIRED",
    }),
]


@pytest.mark.parametrize(
    "label,action,actor_kind,expected",
    [
        (label, action, actor_kind, expected)
        for label, action, table in MATRIX
        for actor_kind, expected in table.items()
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_rbac_matrix_row(label, action, actor_kind, expected):
    session = make_session()
    try:
        ctx = build_scenario(session, actor_kind)
        principal = ctx["principal"]
        if "cross-org" in label:
            target_id = ctx["other_id"]
        elif "remove.admin" in label:
            target_id = ctx["admin_id"]
        else:
            target_id = ctx["victim_id"]
        if "proj." in label:
            result = expect(
                action, session, principal, project_id=ctx["project_id"], target_id=target_id
            )
        else:
            result = expect(action, session, principal, target_id=target_id)
        assert result == expected, f"{label} [{actor_kind}]: expected {expected!r}, got {result!r}"
    finally:
        session.close()
