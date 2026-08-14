from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.knowledge.context_engine import ContextEngine
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_rebuild_indexes_from_persisted_assets(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(
            org_id="org_1",
            name="df-new-bigdata",
            slug="df-new-bigdata",
            git_remotes=["git@example.com:df-new-bigdata.git"],
        )
        AssetRepository(session).create(
            org_id="org_1",
            project_id=project.id,
            type="code_file",
            source="git",
            source_uri="df-new-rtdw/src/main/java/TripDriverBehaviorsNevJob.java",
            title="TripDriverBehaviorsNevJob.java",
            content="Flink Kafka trip driver behavior job.",
        )
        project_id = project.id
        uow.commit()
    session.close()

    restored_session = sessionmaker(bind=create_app_engine(database_url))()
    keyword_index = FakeKeywordIndex()
    vector_index = FakeVectorIndex()

    rebuild_indexes_from_assets(restored_session, keyword_index, vector_index)

    context = ContextEngine(keyword_index=keyword_index, vector_index=vector_index).plan_context(
        org_id="org_1",
        project_id=project_id,
        intent="analysis",
        query="Flink Kafka",
    )

    assert "TripDriverBehaviorsNevJob" in context.summary
