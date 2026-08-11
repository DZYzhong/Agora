from dataclasses import dataclass

from packages.harness.context_planner import ContextPlanner
from packages.harness.development_capture import capture_development_change
from packages.harness.project_resolver import ProjectResolver
from packages.harness.session_recorder import SessionRecorder
from packages.harness.task_resolver import TaskResolver


@dataclass(frozen=True)
class WorkStartResult:
    session_id: str | None
    project: object | None
    task_id: str | None
    intent: str | None
    next_action: str
    clarification: str | None = None


class HarnessService:
    def __init__(self, *, core, context_engine):
        self.core = core
        self.context_engine = context_engine
        self.project_resolver = ProjectResolver(core)
        self.task_resolver = TaskResolver()
        self.session_recorder = SessionRecorder(core)
        self.context_planner = ContextPlanner(core=core, context_engine=context_engine)

    def start_work(self, *, user_message: str, repo_remote: str | None = None, agent_type: str, project_id: str | None = None):
        project = self.core.get_project(project_id) if project_id and hasattr(self.core, "get_project") else None
        if project is None:
            project_resolution = self.project_resolver.resolve(repo_remote=repo_remote, user_message=user_message)
            project = project_resolution.project
            clarification = project_resolution.clarification
        else:
            clarification = None

        if project is None:
            return WorkStartResult(
                session_id=None,
                project=None,
                task_id=None,
                intent=None,
                next_action="ask_user",
                clarification=clarification,
            )

        task_resolution = self.task_resolver.resolve(user_message=user_message)
        session = self.session_recorder.start(
            org_id=project.org_id,
            project_id=project.id,
            agent_type=agent_type,
            intent=task_resolution.intent,
            task_id=task_resolution.task_id,
        )
        return WorkStartResult(
            session_id=session.id,
            project=project,
            task_id=task_resolution.task_id,
            intent=task_resolution.intent,
            next_action="plan_context",
        )

    def plan_context(self, *, session_id: str, query: str | None = None, token_budget: int = 4000):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return self.context_planner.plan(session_id=session_id, query=query or session.intent, token_budget=token_budget)

    def record_event(self, *, session_id: str, event_type: str, payload: dict):
        return self.session_recorder.record_event(session_id=session_id, event_type=event_type, payload=payload)

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
        return result
