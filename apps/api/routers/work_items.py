from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.runtime import CoreRuntime

router = APIRouter(prefix="/projects/{project_id}/work-items", tags=["work-items"])


@router.get("")
def list_work_items(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    runtime = CoreRuntime(session)
    return [_serialize_work_item_projection(runtime, work_item) for work_item, _session_count in runtime.list_work_items_by_project(project_id)]


@router.get("/{work_item_id}")
def get_work_item(
    project_id: str,
    work_item_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_project_member(session, principal, project_id=project_id)
    runtime = CoreRuntime(session)
    work_item = runtime.get_work_item_by_project(project_id=project_id, work_item_id=work_item_id)
    if work_item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    return {
        **_serialize_work_item_projection(runtime, work_item),
        "sessions": [_serialize_work_session(runtime, session_view) for session_view in runtime.list_work_sessions_by_work_item(work_item_id)],
    }


def _serialize_work_item_projection(runtime: CoreRuntime, work_item) -> dict:
    session_views = runtime.list_work_sessions_by_work_item(work_item.id)
    return {
        "id": work_item.id,
        "project_id": work_item.project_id,
        "external_key": work_item.external_key,
        "title": work_item.title,
        "description": work_item.description,
        "status": work_item.status,
        "stage": work_item.stage,
        "source": work_item.source,
        "session_count": len(session_views),
        "participants": sorted({session_view.session.user_id for session_view in session_views}),
        "latest_context_state": _latest_context_state(runtime, session_views),
        "capability_pins": _capability_pins(work_item),
        "workflow_execution": _workflow_execution(runtime, work_item),
    }


def _serialize_work_session(runtime: CoreRuntime, session_view) -> dict:
    events = runtime.list_session_events(session_view.id)
    return {
        "id": session_view.id,
        "project_id": session_view.project_id,
        "task_id": session_view.task_id,
        "work_item": {
            "id": session_view.work_item.id,
            "project_id": session_view.work_item.project_id,
            "external_key": session_view.work_item.external_key,
            "title": session_view.work_item.title,
            "status": session_view.work_item.status,
            "stage": session_view.work_item.stage,
            "source": session_view.work_item.source,
        },
        "agent_type": session_view.agent_type,
        "intent": session_view.intent,
        "status": session_view.status,
        "created_at": session_view.created_at,
        "closed_at": session_view.closed_at,
        "audit_counts": {
            "events": len(events),
            "context_states": len([event for event in events if event.event_type in {"context_prepared", "context_planned"}]),
            "development_updates": len([event for event in events if event.event_type == "development_update_captured"]),
        },
    }


def _latest_context_state(runtime: CoreRuntime, session_views) -> dict | None:
    latest = None
    for session_view in session_views:
        for event in runtime.list_session_events(session_view.id):
            if event.event_type not in {"context_prepared", "context_planned"}:
                continue
            if latest is None or event.created_at > latest["created_at"]:
                payload = event.payload or {}
                latest = {
                    "session_id": session_view.id,
                    "event_type": event.event_type,
                    "context_pack_id": payload.get("context_pack_id"),
                    "provisional": True,
                    "freshness": payload.get("freshness")
                    or {
                        "repository_relation": "unknown",
                        "workspace_state": "unknown",
                        "context_coverage": "potentially_stale",
                        "proposal_state": "none",
                        "accepted_revision_id": None,
                        "observed_commit_sha": None,
                        "recommended_action": "use_provisional_context",
                    },
                    "budget": payload.get("budget"),
                    "created_at": event.created_at,
                }
    return latest


def _capability_pins(work_item) -> dict:
    return {
        "context_revision_id": None,
        "workflow_version_id": work_item.workflow_version_id,
        "skill_version_id": None,
    }


def _workflow_execution(runtime: CoreRuntime, work_item) -> dict | None:
    execution = runtime.get_workflow_execution_by_work_item(work_item.id)
    if execution is None:
        return None
    artifacts_by_step_run = _group_by_step_run(runtime.list_work_artifacts_by_execution(execution.id))
    confirmations_by_step_run = _group_by_step_run(runtime.list_human_confirmations_by_execution(execution.id))
    return {
        "id": execution.id,
        "workflow_version_id": execution.workflow_version_id,
        "status": execution.status,
        "current_step_key": execution.current_step_key,
        "steps": [
            {
                "id": step.id,
                "step_key": step.step_key,
                "title": step.title,
                "order_index": step.order_index,
                "status": step.status,
                "required_artifacts": step.required_artifacts,
                "artifacts": [_serialize_work_artifact(artifact) for artifact in artifacts_by_step_run.get(step.id, [])],
                "human_confirmations": [
                    _serialize_human_confirmation(confirmation)
                    for confirmation in confirmations_by_step_run.get(step.id, [])
                ],
            }
            for step in runtime.list_workflow_step_runs(execution.id)
        ],
    }


def _group_by_step_run(records) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for record in records:
        grouped.setdefault(record.workflow_step_run_id, []).append(record)
    return grouped


def _serialize_work_artifact(artifact) -> dict:
    return {
        "id": artifact.id,
        "session_id": artifact.session_id,
        "workflow_step_run_id": artifact.workflow_step_run_id,
        "step_key": artifact.step_key,
        "type": artifact.type,
        "title": artifact.title,
        "content": artifact.content,
        "metadata": artifact.artifact_metadata,
        "created_by_user_id": artifact.created_by_user_id,
        "created_at": artifact.created_at,
    }


def _serialize_human_confirmation(confirmation) -> dict:
    return {
        "id": confirmation.id,
        "session_id": confirmation.session_id,
        "workflow_step_run_id": confirmation.workflow_step_run_id,
        "step_key": confirmation.step_key,
        "confirmation_type": confirmation.confirmation_type,
        "decision": confirmation.decision,
        "comment": confirmation.comment,
        "confirmed_by_user_id": confirmation.confirmed_by_user_id,
        "created_at": confirmation.created_at,
    }
