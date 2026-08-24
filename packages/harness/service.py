from dataclasses import dataclass

from packages.core.auth import Principal
from packages.core.models import utc_now
from packages.domain.local_workspace import LocalWorkspaceObservation
from packages.harness.context_planner import ContextPlanner
from packages.harness.development_capture import capture_development_change
from packages.harness.project_resolver import ProjectResolver
from packages.harness.session_recorder import SessionRecorder
from packages.harness.work_resolver import WorkResolver


@dataclass(frozen=True)
class WorkStartResult:
    session_id: str | None
    project: object | None
    work_item_id: str | None
    work_item_title: str | None
    task_id: str | None
    intent: str | None
    next_action: str
    clarification: str | None = None
    context_revision_id: str | None = None
    workflow_version_id: str | None = None
    skill_version_id: str | None = None


@dataclass(frozen=True)
class ContextRefResult:
    session_id: str
    asset_id: str
    title: str
    source_uri: str
    type: str
    content: str
    truncated: bool
    metadata: dict


class HarnessService:
    def __init__(self, *, core, context_engine):
        self.core = core
        self.context_engine = context_engine
        self.project_resolver = ProjectResolver(core)
        self.work_resolver = WorkResolver(core)
        self.session_recorder = SessionRecorder(core)
        self.context_planner = ContextPlanner(core=core, context_engine=context_engine)

    def start_work(
        self,
        *,
        user_message: str,
        repo_remote: str | None = None,
        agent_type: str,
        project_id: str | None = None,
        principal: Principal | None = None,
        branch_name: str | None = None,
        local_observation: LocalWorkspaceObservation | dict | None = None,
        initial_request_id: str | None = None,
    ):
        if principal is None:
            raise ValueError("HarnessService.start_work requires an authenticated Principal")
        observation = _coerce_local_observation(local_observation)
        observed_branch_name = observation.branch_name if observation is not None else None
        effective_branch_name = branch_name or observed_branch_name
        project = self.core.get_project(project_id) if project_id and hasattr(self.core, "get_project") else None
        if project is None:
            project_resolution = self.project_resolver.resolve(
                repo_remote=repo_remote,
                user_message=user_message,
                local_observation=observation,
            )
            project = project_resolution.project
            clarification = project_resolution.clarification
        else:
            clarification = None

        if project is None:
            return WorkStartResult(
                session_id=None,
                project=None,
                work_item_id=None,
                work_item_title=None,
                task_id=None,
                intent=None,
                next_action="ask_user",
                clarification=clarification,
            )

        work_resolution = self.work_resolver.resolve(
            project=project,
            user_message=user_message,
            branch_name=effective_branch_name,
        )
        if work_resolution.next_action == "ask_user":
            return WorkStartResult(
                session_id=None,
                project=project,
                work_item_id=None,
                work_item_title=work_resolution.title,
                task_id=work_resolution.external_key,
                intent=work_resolution.intent,
                next_action="ask_user",
                clarification=work_resolution.clarification,
            )

        session = self.session_recorder.start(
            work_item_id=work_resolution.work_item.id,
            user_id=principal.user_id,
            credential_id=principal.credential_id,
            agent_type=agent_type,
            intent=work_resolution.intent,
            initial_request_id=initial_request_id,
        )
        return WorkStartResult(
            session_id=session.id,
            project=project,
            work_item_id=work_resolution.work_item.id,
            work_item_title=work_resolution.work_item.title,
            task_id=work_resolution.external_key,
            intent=work_resolution.intent,
            next_action="plan_context",
        )

    def plan_context(self, *, session_id: str, query: str | None = None, token_budget: int = 4000):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return self.context_planner.plan(session_id=session_id, query=query or session.intent, token_budget=token_budget)

    def prepare_context(
        self,
        *,
        session_id: str,
        query: str | None = None,
        token_budget: int = 4000,
        event_type: str = "context_prepared",
    ):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return self.context_planner.prepare(
            session_id=session_id,
            query=query or session.intent,
            token_budget=token_budget,
            event_type=event_type,
        )

    def record_event(self, *, session_id: str, event_type: str, payload: dict):
        return self.session_recorder.record_event(session_id=session_id, event_type=event_type, payload=payload)

    def fetch_context_ref(self, *, session_id: str, asset_id: str, max_tokens: int = 2000):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        asset = self.core.get_asset(asset_id)
        if asset is None or asset.project_id != session.project_id:
            raise ValueError(f"Context source not found: {asset_id}")
        max_chars = max(200, max_tokens * 4)
        content = asset.content[:max_chars]
        return ContextRefResult(
            session_id=session_id,
            asset_id=asset.id,
            title=asset.title,
            source_uri=asset.source_uri,
            type=asset.type,
            content=content,
            truncated=len(asset.content) > len(content),
            metadata=asset.asset_metadata or {},
        )

    def close_work(
        self,
        *,
        session_id: str,
        status: str = "closed",
        repo_path: str | None = None,
        base_ref: str = "HEAD",
        head_ref: str | None = None,
        agent_summary: str | None = None,
        test_result: str | None = None,
    ):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        session.status = status
        session.closed_at = utc_now()
        writeback = None
        if repo_path or agent_summary or test_result:
            change = capture_development_change(
                repo_path=repo_path,
                base_ref=base_ref,
                head_ref=head_ref,
                agent_summary=agent_summary,
                test_result=test_result,
                session_intent=session.intent,
            )
            writeback = self.core.create_writeback(
                org_id=session.org_id,
                project_id=session.project_id,
                session_id=session_id,
                type="development_update",
                title=change.title,
                content=change.content,
                asset_refs=[],
                status="draft",
            )
            self.session_recorder.record_event(
                session_id=session_id,
                event_type="development_update_captured",
                payload={
                    "writeback_id": writeback.id,
                    "writeback_type": "development_update",
                    "development_update": change.structured,
                },
            )
        result = {"session_id": session_id, "status": status}
        if writeback is not None:
            result["writeback"] = {
                "id": writeback.id,
                "project_id": writeback.project_id,
                "session_id": writeback.session_id,
                "type": writeback.type,
                "title": writeback.title,
                "content": writeback.content,
                "status": writeback.status,
            }
            result["development_update"] = change.structured
        return result


def _coerce_local_observation(
    local_observation: LocalWorkspaceObservation | dict | None,
) -> LocalWorkspaceObservation | None:
    if local_observation is None:
        return None
    if isinstance(local_observation, LocalWorkspaceObservation):
        return local_observation
    return LocalWorkspaceObservation.model_validate(local_observation)
