from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.core.database import Base
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository


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
