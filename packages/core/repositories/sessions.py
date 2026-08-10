from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import SessionEventModel, TaskSessionModel


class TaskSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, org_id: str, project_id: str, agent_type: str, intent: str, task_id: str | None = None) -> TaskSessionModel:
        task_session = TaskSessionModel(org_id=org_id, project_id=project_id, task_id=task_id, agent_type=agent_type, intent=intent)
        self.session.add(task_session)
        self.session.commit()
        self.session.refresh(task_session)
        return task_session

    def get(self, session_id: str) -> TaskSessionModel | None:
        return self.session.get(TaskSessionModel, session_id)

    def list_by_project(self, project_id: str) -> list[TaskSessionModel]:
        statement = select(TaskSessionModel).where(TaskSessionModel.project_id == project_id)
        return list(self.session.scalars(statement).all())

    def record_event(self, *, session_id: str, event_type: str, payload: dict) -> SessionEventModel:
        event = SessionEventModel(session_id=session_id, event_type=event_type, payload=payload)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
