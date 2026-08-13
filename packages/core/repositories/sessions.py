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

    def list_by_project(
        self,
        project_id: str,
        *,
        intent: str | None = None,
        status: str | None = None,
    ) -> list[TaskSessionModel]:
        statement = select(TaskSessionModel).where(TaskSessionModel.project_id == project_id).order_by(TaskSessionModel.created_at.desc())
        if intent:
            statement = statement.where(TaskSessionModel.intent == intent)
        if status:
            statement = statement.where(TaskSessionModel.status == status)
        return list(self.session.scalars(statement).all())

    def get_by_project(self, *, project_id: str, session_id: str) -> TaskSessionModel | None:
        statement = select(TaskSessionModel).where(TaskSessionModel.project_id == project_id, TaskSessionModel.id == session_id)
        return self.session.scalars(statement).first()

    def record_event(self, *, session_id: str, event_type: str, payload: dict) -> SessionEventModel:
        event = SessionEventModel(session_id=session_id, event_type=event_type, payload=payload)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_events(self, session_id: str) -> list[SessionEventModel]:
        statement = select(SessionEventModel).where(SessionEventModel.session_id == session_id).order_by(SessionEventModel.created_at.asc())
        return list(self.session.scalars(statement).all())
