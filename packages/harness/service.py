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


@dataclass(frozen=True)
class ContextProposalSubmission:
    protocol_version: str
    operation: str
    proposal: dict
    stream: dict
    capability_pins: dict
    next_actions: list[dict]


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

        workflow_version_id = None
        workflow_execution_id = None
        if hasattr(self.core, "ensure_standard_workflow_version") and hasattr(self.core, "ensure_workflow_execution_for_work_item"):
            workflow_version = self.core.ensure_standard_workflow_version(org_id=project.org_id, project_id=project.id)
            workflow_execution = self.core.ensure_workflow_execution_for_work_item(
                work_item=work_resolution.work_item,
                workflow_version=workflow_version,
            )
            workflow_version_id = workflow_version.id
            workflow_execution_id = workflow_execution.id

        session = self.session_recorder.start(
            work_item_id=work_resolution.work_item.id,
            user_id=principal.user_id,
            credential_id=principal.credential_id,
            agent_type=agent_type,
            intent=work_resolution.intent,
            initial_request_id=initial_request_id,
            workflow_version_id=workflow_version_id,
            workflow_execution_id=workflow_execution_id,
        )
        return WorkStartResult(
            session_id=session.id,
            project=project,
            work_item_id=work_resolution.work_item.id,
            work_item_title=work_resolution.work_item.title,
            task_id=work_resolution.external_key,
            intent=work_resolution.intent,
            next_action="plan_context",
            workflow_version_id=workflow_version_id,
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

    def submit_context_proposal(
        self,
        *,
        session_id: str,
        type: str,
        title: str,
        summary: str,
        target_branch: str = "main",
        expected_head_revision_id: str | None = None,
        from_commit_sha: str | None = None,
        to_commit_sha: str | None = None,
        content: dict | None = None,
        source_anchors: list[dict] | None = None,
        provenance: dict | None = None,
        principal: Principal | None = None,
    ) -> ContextProposalSubmission:
        if principal is None:
            raise ValueError("HarnessService.submit_context_proposal requires an authenticated Principal")
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        project = self.core.get_project(session.project_id)
        if project is None:
            raise ValueError(f"Project not found: {session.project_id}")

        branch = target_branch or project.default_branch or "main"
        stream = self.core.ensure_context_stream(
            org_id=session.org_id,
            project_id=session.project_id,
            branch=branch,
            repository_identity={"git_remotes": project.git_remotes},
        )
        work_item = getattr(session, "work_item", None)
        proposal = self.core.create_context_proposal(
            org_id=session.org_id,
            project_id=session.project_id,
            stream_id=stream.id,
            work_item_id=getattr(work_item, "id", None) or getattr(session, "work_item_id", None),
            session_id=session_id,
            type=type,
            status="submitted",
            title=title,
            summary=summary,
            content=content or {},
            source_anchors=source_anchors or [],
            provenance=provenance or {},
            target_branch=stream.branch,
            expected_head_revision_id=expected_head_revision_id,
            from_commit_sha=from_commit_sha,
            to_commit_sha=to_commit_sha,
            created_by_user_id=principal.user_id,
        )
        return ContextProposalSubmission(
            protocol_version="1.0",
            operation="submit_context_proposal",
            proposal=_serialize_context_proposal(self.core, proposal),
            stream=_serialize_context_stream(stream),
            capability_pins={"context_revision_id": stream.head_revision_id},
            next_actions=[
                {
                    "type": "human_review_context_proposal",
                    "reason": "Context proposal was submitted and requires human review before becoming the accepted project context.",
                }
            ],
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


def _serialize_context_stream(stream) -> dict:
    return {
        "id": stream.id,
        "project_id": stream.project_id,
        "name": stream.name,
        "branch": stream.branch,
        "head_revision_id": stream.head_revision_id,
        "status": stream.status,
        "repository_identity": stream.repository_identity,
        "created_at": stream.created_at,
        "updated_at": stream.updated_at,
    }


def _serialize_context_proposal(core, proposal) -> dict:
    stream = core.get_context_stream(proposal.stream_id)
    return {
        "id": proposal.id,
        "project_id": proposal.project_id,
        "stream_id": proposal.stream_id,
        "stream": _serialize_context_stream(stream) if stream else None,
        "work_item_id": proposal.work_item_id,
        "session_id": proposal.session_id,
        "type": proposal.type,
        "status": proposal.status,
        "title": proposal.title,
        "summary": proposal.summary,
        "content": proposal.content,
        "source_anchors": proposal.source_anchors,
        "provenance": proposal.provenance,
        "target_branch": proposal.target_branch,
        "expected_head_revision_id": proposal.expected_head_revision_id,
        "from_commit_sha": proposal.from_commit_sha,
        "to_commit_sha": proposal.to_commit_sha,
        "accepted_revision_id": proposal.accepted_revision_id,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
    }
