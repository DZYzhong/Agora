from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.runtime import CoreRuntime

router = APIRouter(prefix="/projects/{project_id}/sessions", tags=["sessions"])


@router.get("")
def list_sessions(
    project_id: str,
    intent: str | None = None,
    status: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_db_session),
):
    runtime = CoreRuntime(session)
    task_sessions = runtime.list_sessions_by_project(project_id, intent=intent, status=status)
    audits = [_serialize_session_audit(runtime, task_session) for task_session in task_sessions]
    if q:
        audits = [audit for audit in audits if _matches_query(audit, q)]
    return audits


@router.get("/{session_id}")
def get_session_detail(project_id: str, session_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    task_session = runtime.get_session_by_project(project_id=project_id, session_id=session_id)
    if task_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session_audit(runtime, task_session)


def _serialize_session_audit(runtime: CoreRuntime, task_session) -> dict:
    events = runtime.list_session_events(task_session.id)
    context_pack_ids = [
        event.payload["context_pack_id"]
        for event in events
        if event.event_type == "context_planned" and event.payload.get("context_pack_id")
    ]
    context_packs = runtime.list_context_packs_by_ids(context_pack_ids)
    skill_runs = runtime.list_skill_runs_by_session(project_id=task_session.project_id, session_id=task_session.id)
    writebacks = runtime.list_writebacks_by_session(project_id=task_session.project_id, session_id=task_session.id)
    skills_by_id = {
        skill.id: skill
        for skill in runtime.list_skills_by_project(task_session.project_id)
    }
    audit_counts = {
        "events": len(events),
        "context_packs": len(context_packs),
        "skill_runs": len(skill_runs),
        "writebacks": len(writebacks),
    }
    return {
        "id": task_session.id,
        "project_id": task_session.project_id,
        "task_id": task_session.task_id,
        "agent_type": task_session.agent_type,
        "intent": task_session.intent,
        "status": task_session.status,
        "created_at": task_session.created_at,
        "closed_at": task_session.closed_at,
        "audit_counts": audit_counts,
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
        "skill_runs": [
            {
                "id": run.id,
                "skill_id": run.skill_id,
                "skill_name": skills_by_id[run.skill_id].name if run.skill_id in skills_by_id else run.skill_id,
                "input": run.input,
                "output": run.output,
                "warnings": run.warnings,
                "status": run.status,
                "created_at": run.created_at,
            }
            for run in skill_runs
        ],
        "writebacks": [
            {
                "id": writeback.id,
                "type": writeback.type,
                "title": writeback.title,
                "content": writeback.content,
                "asset_refs": writeback.asset_refs,
                "status": writeback.status,
                "accepted_asset_id": writeback.accepted_asset_id,
                "created_at": writeback.created_at,
            }
            for writeback in writebacks
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


def _matches_query(audit: dict, query: str) -> bool:
    needle = query.casefold()
    haystack = " ".join(_flatten_for_search(audit)).casefold()
    return needle in haystack


def _flatten_for_search(value) -> list[str]:
    if isinstance(value, dict):
        terms: list[str] = []
        for item in value.values():
            terms.extend(_flatten_for_search(item))
        return terms
    if isinstance(value, list):
        terms = []
        for item in value:
            terms.extend(_flatten_for_search(item))
        return terms
    if value is None:
        return []
    return [str(value)]
