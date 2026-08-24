from pydantic import BaseModel, Field

from packages.domain.enums import WritebackStatus


class ProjectCreate(BaseModel):
    org_id: str
    name: str
    slug: str
    description: str | None = None
    git_remotes: list[str] = Field(default_factory=list)
    default_branch: str | None = None


class ProjectRead(ProjectCreate):
    id: str
    status: str = "active"


class AssetCreate(BaseModel):
    org_id: str
    project_id: str
    type: str
    source: str
    source_uri: str
    title: str
    content: str
    summary: str | None = None
    metadata: dict = Field(default_factory=dict)
    content_hash: str | None = None


class ContextPackRead(BaseModel):
    id: str
    org_id: str
    project_id: str
    level: str
    summary: str
    key_facts: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)


class ContextBundleRead(ContextPackRead):
    protocol_version: str = "1.0"
    operation: str = "prepare_context"
    session_id: str
    context_pack_id: str
    intent: str
    query: str
    provisional: bool = True
    freshness: dict
    budget: dict
    next_actions: list[dict] = Field(default_factory=list)


class WritebackCreate(BaseModel):
    org_id: str
    project_id: str
    type: str
    title: str
    content: str
    session_id: str | None = None
    asset_refs: list[str] = Field(default_factory=list)
    status: WritebackStatus = WritebackStatus.DRAFT
