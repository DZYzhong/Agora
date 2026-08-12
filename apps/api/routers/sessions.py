from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.runtime import CoreRuntime

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["sessions"])


@router.get("")
def list_sessions(project_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    task_sessions = runtime.list_sessions_by_project(project_id)
    return [
        {
            "id": task_session.id,
            "project_id": task_session.project_id,
            "task_id": task_session.task_id,
            "agent_type": task_session.agent_type,
            "intent": task_session.intent,
            "status": task_session.status,
            "created_at": task_session.created_at,
            "closed_at": task_session.closed_at,
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
                for event in runtime.list_session_events(task_session.id)
            ],
        }
        for task_session in task_sessions
    ]
