from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import (
    HumanConfirmationModel,
    WorkArtifactModel,
    WorkflowDefinitionModel,
    WorkflowExecutionModel,
    WorkflowStepRunModel,
    WorkflowVersionModel,
    WorkItemModel,
)


STANDARD_WORKFLOW_SLUG = "standard-ai-development"
STANDARD_WORKFLOW_STEPS = [
    {"key": "analysis", "title": "Analysis", "required_artifacts": [{"type": "analysis_note"}]},
    {"key": "design", "title": "Design", "required_artifacts": [{"type": "design_note"}]},
    {"key": "review", "title": "Review", "required_artifacts": [{"type": "review_note"}]},
    {"key": "implementation", "title": "Implementation", "required_artifacts": [{"type": "code_change"}]},
    {"key": "self_test", "title": "Self-test", "required_artifacts": [{"type": "test_result"}]},
    {"key": "delivery", "title": "Delivery", "required_artifacts": [{"type": "delivery_note"}]},
]


class WorkflowRepository:
    def __init__(self, session: Session):
        self.session = session

    def ensure_standard_workflow_version(self, *, org_id: str, project_id: str | None = None) -> WorkflowVersionModel:
        definition = self.get_definition_by_slug(org_id=org_id, project_id=project_id, slug=STANDARD_WORKFLOW_SLUG)
        if definition is None:
            definition = WorkflowDefinitionModel(
                org_id=org_id,
                project_id=project_id,
                slug=STANDARD_WORKFLOW_SLUG,
                name="Standard AI development workflow",
                status="active",
            )
            self.session.add(definition)
            self.session.flush()
            self.session.refresh(definition)
        version = self.get_version_by_definition(definition.id, version="1")
        if version is not None:
            return version
        version = WorkflowVersionModel(
            org_id=org_id,
            project_id=project_id,
            workflow_definition_id=definition.id,
            version="1",
            status="approved",
            steps=STANDARD_WORKFLOW_STEPS,
            policy={
                "human_gates": ["review", "delivery"],
                "artifact_policy": "required_before_step_completion",
            },
        )
        self.session.add(version)
        self.session.flush()
        self.session.refresh(version)
        return version

    def get_definition_by_slug(
        self,
        *,
        org_id: str,
        project_id: str | None,
        slug: str,
    ) -> WorkflowDefinitionModel | None:
        statement = select(WorkflowDefinitionModel).where(
            WorkflowDefinitionModel.org_id == org_id,
            WorkflowDefinitionModel.slug == slug,
        )
        if project_id is None:
            statement = statement.where(WorkflowDefinitionModel.project_id.is_(None))
        else:
            statement = statement.where(WorkflowDefinitionModel.project_id == project_id)
        return self.session.scalars(statement).first()

    def get_version_by_definition(self, workflow_definition_id: str, *, version: str) -> WorkflowVersionModel | None:
        statement = select(WorkflowVersionModel).where(
            WorkflowVersionModel.workflow_definition_id == workflow_definition_id,
            WorkflowVersionModel.version == version,
        )
        return self.session.scalars(statement).first()

    def get_execution_by_work_item(self, work_item_id: str) -> WorkflowExecutionModel | None:
        statement = select(WorkflowExecutionModel).where(WorkflowExecutionModel.work_item_id == work_item_id)
        return self.session.scalars(statement).first()

    def ensure_execution_for_work_item(
        self,
        *,
        work_item: WorkItemModel,
        workflow_version: WorkflowVersionModel,
    ) -> WorkflowExecutionModel:
        execution = self.get_execution_by_work_item(work_item.id)
        if execution is not None:
            return execution
        first_step = workflow_version.steps[0]
        execution = WorkflowExecutionModel(
            org_id=work_item.org_id,
            project_id=work_item.project_id,
            work_item_id=work_item.id,
            workflow_version_id=workflow_version.id,
            status="running",
            current_step_key=first_step["key"],
        )
        self.session.add(execution)
        self.session.flush()
        self.session.refresh(execution)
        for index, step in enumerate(workflow_version.steps):
            self.session.add(
                WorkflowStepRunModel(
                    org_id=work_item.org_id,
                    project_id=work_item.project_id,
                    workflow_execution_id=execution.id,
                    work_item_id=work_item.id,
                    step_key=step["key"],
                    title=step["title"],
                    order_index=index,
                    status="running" if index == 0 else "pending",
                    required_artifacts=step.get("required_artifacts", []),
                )
            )
        work_item.workflow_version_id = workflow_version.id
        work_item.workflow_execution_id = execution.id
        work_item.stage = first_step["key"]
        self.session.flush()
        self.session.refresh(work_item)
        return execution

    def list_step_runs(self, workflow_execution_id: str) -> list[WorkflowStepRunModel]:
        statement = (
            select(WorkflowStepRunModel)
            .where(WorkflowStepRunModel.workflow_execution_id == workflow_execution_id)
            .order_by(WorkflowStepRunModel.order_index)
        )
        return list(self.session.scalars(statement).all())

    def complete_current_step(
        self,
        *,
        workflow_execution_id: str,
        step_key: str,
    ) -> tuple[WorkflowExecutionModel, WorkflowStepRunModel, WorkflowStepRunModel | None]:
        execution = self.session.get(WorkflowExecutionModel, workflow_execution_id)
        if execution is None:
            raise WorkflowStepError("WORKFLOW_EXECUTION_NOT_FOUND", f"Workflow execution not found: {workflow_execution_id}")
        if execution.status != "running" or execution.current_step_key is None:
            raise WorkflowStepError("WORKFLOW_ALREADY_COMPLETED", "Workflow execution is not running")
        if execution.current_step_key != step_key:
            raise WorkflowStepError(
                "WORKFLOW_STEP_NOT_CURRENT",
                f"Current workflow step is {execution.current_step_key}; cannot complete {step_key}",
            )
        steps = self.list_step_runs(workflow_execution_id)
        current_index = next((index for index, step in enumerate(steps) if step.step_key == step_key), None)
        if current_index is None:
            raise WorkflowStepError("WORKFLOW_STEP_NOT_FOUND", f"Workflow step not found: {step_key}")

        completed_step = steps[current_index]
        if completed_step.status != "running":
            raise WorkflowStepError("WORKFLOW_STEP_NOT_RUNNING", f"Workflow step is not running: {step_key}")

        completed_step.status = "completed"
        next_step = steps[current_index + 1] if current_index + 1 < len(steps) else None
        work_item = self.session.get(WorkItemModel, execution.work_item_id)
        if next_step is None:
            execution.status = "completed"
            execution.current_step_key = None
            if work_item is not None:
                work_item.status = "completed"
                work_item.stage = completed_step.step_key
        else:
            next_step.status = "running"
            execution.current_step_key = next_step.step_key
            if work_item is not None:
                work_item.stage = next_step.step_key
        self.session.flush()
        self.session.refresh(execution)
        self.session.refresh(completed_step)
        if next_step is not None:
            self.session.refresh(next_step)
        return execution, completed_step, next_step

    def create_work_artifact(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str,
        session_id: str,
        workflow_execution_id: str,
        workflow_step_run_id: str,
        step_key: str,
        type: str,
        title: str,
        content: str,
        metadata: dict | None,
        created_by_user_id: str,
    ) -> WorkArtifactModel:
        artifact = WorkArtifactModel(
            org_id=org_id,
            project_id=project_id,
            work_item_id=work_item_id,
            session_id=session_id,
            workflow_execution_id=workflow_execution_id,
            workflow_step_run_id=workflow_step_run_id,
            step_key=step_key,
            type=type,
            title=title,
            content=content,
            artifact_metadata=metadata or {},
            created_by_user_id=created_by_user_id,
        )
        self.session.add(artifact)
        self.session.flush()
        self.session.refresh(artifact)
        return artifact

    def create_human_confirmation(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str,
        session_id: str,
        workflow_execution_id: str,
        workflow_step_run_id: str,
        step_key: str,
        confirmation_type: str,
        decision: str,
        comment: str | None,
        confirmed_by_user_id: str,
    ) -> HumanConfirmationModel:
        confirmation = HumanConfirmationModel(
            org_id=org_id,
            project_id=project_id,
            work_item_id=work_item_id,
            session_id=session_id,
            workflow_execution_id=workflow_execution_id,
            workflow_step_run_id=workflow_step_run_id,
            step_key=step_key,
            confirmation_type=confirmation_type,
            decision=decision,
            comment=comment,
            confirmed_by_user_id=confirmed_by_user_id,
        )
        self.session.add(confirmation)
        self.session.flush()
        self.session.refresh(confirmation)
        return confirmation


class WorkflowStepError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
