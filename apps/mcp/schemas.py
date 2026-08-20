from pydantic import BaseModel

from packages.domain.local_workspace import LocalWorkspaceObservation


class StartWorkInput(BaseModel):
    user_message: str
    repo_remote: str | None = None
    branch_name: str | None = None
    local_observation: LocalWorkspaceObservation | None = None
    agent_type: str


class PlanContextInput(BaseModel):
    session_id: str
    query: str | None = None
    token_budget: int = 4000


class RunSkillInput(BaseModel):
    session_id: str
    skill_slug: str
    input: dict


class RecordEventInput(BaseModel):
    session_id: str
    event_type: str
    payload: dict


class PrepareWritebackInput(BaseModel):
    session_id: str
    agent_summary: str
    diff_summary: str | None = None
    test_result: str | None = None


class CloseWorkInput(BaseModel):
    session_id: str
    status: str = "closed"
    repo_path: str | None = None
    base_ref: str = "HEAD"
    head_ref: str | None = None
    agent_summary: str | None = None
    test_result: str | None = None
