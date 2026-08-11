from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.repositories.projects import ProjectRepository


def test_file_sqlite_engine_persists_projects_across_engine_recreation(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    first_engine = create_app_engine(database_url)
    Base.metadata.create_all(first_engine)
    first_session = sessionmaker(bind=first_engine)()
    project = ProjectRepository(first_session).create(
        org_id="org_1",
        name="Persisted",
        slug="persisted",
        git_remotes=["git@example.com:persisted.git"],
    )
    first_session.close()
    first_engine.dispose()

    second_engine = create_app_engine(database_url)
    Base.metadata.create_all(second_engine)
    second_session = sessionmaker(bind=second_engine)()
    loaded = ProjectRepository(second_session).get(project.id)
    second_session.close()
    second_engine.dispose()

    assert loaded is not None
    assert loaded.slug == "persisted"
