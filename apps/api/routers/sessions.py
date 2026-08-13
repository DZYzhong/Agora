from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.runtime import CoreRuntime

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["sessions"])


@router.get("")
def list_sessions(project_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    task_sessions = runtime.list_sessions_by_project(project_id)
    response = []
    for task_session in task_sessions:
        events = runtime.list_session_events(task_session.id)
        context_pack_ids = [
            event.payload["context_pack_id"]
            for event in events
            if event.event_type == "context_planned" and event.payload.get("context_pack_id")
        ]
        context_packs = runtime.list_context_packs_by_ids(context_pack_ids)
        response.append(
            {
                "id": task_session.id,
                "project_id": task_session.project_id,
                "task_id": task_session.task_id,
                "agent_type": task_session.agent_type,
                "intent": task_session.intent,
                "status": task_session.status,
                "created_at": task_session.created_at,
                "closed_at": task_session.closed_at,
                "context_packs": [
                    {
                        "id": context_pack.id,
                        "level": context_pack.level,
                        "summary": context_pack.summary,
                        "key_facts": context_pack.key_facts,
                        "source_refs": context_pack.source_refs,
                        "created_at": context_pack.created_at,
                    }
                    for context_pack in context_packs
                ],
                "events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "created_at": event.created_at,
                    }
                    for event in events
                ],
            }
        )
    return response
