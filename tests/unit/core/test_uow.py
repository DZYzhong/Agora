import importlib.util
from importlib import import_module

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from packages.core.database import Base
from packages.core.models import ProjectModel, UserModel, WorkItemModel, WorkSessionModel
from packages.core.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


def test_sqlalchemy_unit_of_work_module_exists():
    assert importlib.util.find_spec("packages.core.uow") is not None


def test_sqlalchemy_unit_of_work_is_public():
    assert hasattr(import_module("packages.core.uow"), "SqlAlchemyUnitOfWork")


def test_explicit_commit_persists_successful_command_without_closing_session(session_factory):
    session = session_factory()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectModel(org_id="org_1", name="Payment", slug="payment")
        session.add(project)
        uow.flush()
        project_id = project.id
        uow.commit()

    assert session.get(ProjectModel, project_id) is not None
    session.close()


def test_exception_rolls_back_flushed_project_work_item_and_work_session(session_factory):
    session = session_factory()

    with pytest.raises(RuntimeError, match="command failed"):
        with SqlAlchemyUnitOfWork(session) as uow:
            project = ProjectModel(org_id="org_1", name="Payment", slug="payment")
            user = UserModel(org_id="org_1", display_name="Developer")
            session.add_all([project, user])
            uow.flush()
            work_item = WorkItemModel(
                org_id="org_1",
                project_id=project.id,
                title="Implement transaction boundary",
            )
            session.add(work_item)
            uow.flush()
            work_session = WorkSessionModel(
                work_item_id=work_item.id,
                user_id=user.id,
                agent_type="codex",
                intent="implementation",
            )
            session.add(work_session)
            uow.flush()
            raise RuntimeError("command failed")

    with session_factory() as verification_session:
        for model in (ProjectModel, WorkItemModel, WorkSessionModel):
            assert verification_session.scalar(select(func.count()).select_from(model)) == 0
    session.close()


def test_clean_exit_without_explicit_commit_rolls_back(session_factory):
    session = session_factory()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectModel(org_id="org_1", name="Payment", slug="payment")
        session.add(project)
        uow.flush()
        project_id = project.id

    with session_factory() as verification_session:
        assert verification_session.get(ProjectModel, project_id) is None
    session.close()


def test_nested_unit_of_work_on_same_session_is_rejected(session_factory):
    session = session_factory()
    with SqlAlchemyUnitOfWork(session):
        with pytest.raises(RuntimeError, match="Nested SqlAlchemyUnitOfWork"):
            with SqlAlchemyUnitOfWork(session):
                pass

    with SqlAlchemyUnitOfWork(session):
        pass
    session.close()
