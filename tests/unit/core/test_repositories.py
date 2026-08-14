import ast
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.core.database import Base
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.uow import SqlAlchemyUnitOfWork


PROJECT_ROOT = Path(__file__).parents[3]


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_project_repository_creates_project():
    session = make_session()
    repo = ProjectRepository(session)

    project = repo.create(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )

    assert project.id
    assert project.org_id == "org_1"
    assert project.git_remotes == ["git@example.com:payment.git"]


def test_project_repository_archives_projects_and_hides_them_from_default_list():
    session = make_session()
    repo = ProjectRepository(session)
    active = repo.create(org_id="org_1", name="Active", slug="active")
    archived = repo.create(org_id="org_1", name="Archived", slug="archived")

    repo.archive(archived.id)

    assert repo.get(archived.id).status == "archived"
    assert [project.id for project in repo.list()] == [active.id]
    assert [project.id for project in repo.list(include_archived=True)] == [active.id, archived.id]


def test_asset_repository_creates_asset():
    session = make_session()
    project = ProjectRepository(session).create(org_id="org_1", name="Payment", slug="payment")
    asset = AssetRepository(session).create(
        org_id="org_1",
        project_id=project.id,
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Payment service",
    )

    assert asset.project_id == project.id
    assert asset.title == "README"


def test_asset_repository_upserts_by_project_and_source_uri():
    session = make_session()
    project = ProjectRepository(session).create(org_id="org_1", name="Payment", slug="payment")
    repo = AssetRepository(session)

    first = repo.upsert_by_source_uri(
        org_id="org_1",
        project_id=project.id,
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Old content",
        content_hash="old",
    )
    second = repo.upsert_by_source_uri(
        org_id="org_1",
        project_id=project.id,
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="New content",
        content_hash="new",
    )

    assets = repo.list_by_project(project.id)
    assert first.id == second.id
    assert len(assets) == 1
    assert assets[0].content == "New content"
    assert assets[0].content_hash == "new"


def test_repository_writes_roll_back_with_the_command_unit_of_work():
    session = make_session()

    with pytest.raises(RuntimeError, match="command failed"):
        with SqlAlchemyUnitOfWork(session):
            project = ProjectRepository(session).create(
                org_id="org_1",
                name="Payment",
                slug="payment",
            )
            AssetRepository(session).create(
                org_id="org_1",
                project_id=project.id,
                type="doc",
                source="git",
                source_uri="README.md",
                title="README",
                content="Payment service",
            )
            raise RuntimeError("command failed")

    assert ProjectRepository(session).list(include_archived=True) == []
    assert AssetRepository(session).list_all() == []


def test_repositories_and_domain_services_do_not_commit_transactions():
    guarded_roots = [
        PROJECT_ROOT / "packages/core/repositories",
        PROJECT_ROOT / "packages/core/services",
        PROJECT_ROOT / "packages/domain",
        PROJECT_ROOT / "packages/harness",
    ]
    offenders = []
    for root in guarded_roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "commit":
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    assert offenders == [], f"Direct commit is forbidden outside application UoW boundaries: {offenders}"
