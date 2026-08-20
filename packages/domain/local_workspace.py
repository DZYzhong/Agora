from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RepositoryIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    path: str
    normalized: str

    @field_validator("host", "path", "normalized")
    @classmethod
    def reject_secrets(cls, value: str) -> str:
        if "@" in value or "://" in value or "\\" in value:
            raise ValueError("repository identity must not contain credentials, schemes, or local paths")
        if value.startswith("/") or ":" in value.split("/", 1)[0]:
            raise ValueError("repository identity must not contain local paths")
        return value


class LocalWorkspaceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: RepositoryIdentity | None = None
    branch_name: str | None = None
    head_commit: str | None = Field(default=None, min_length=7, max_length=64)
    dirty: bool
    changed_file_count: int = Field(default=0, ge=0)
    untracked_file_count: int = Field(default=0, ge=0)
    observer: str = "agora-mcp"

    @model_validator(mode="before")
    @classmethod
    def reject_local_or_secret_fields(cls, data: Any):
        if isinstance(data, dict):
            forbidden = {
                "absolute_path",
                "cwd",
                "local_path",
                "repo_path",
                "repository_path",
                "root",
                "workspace_path",
                "workspace_root",
            }
            if forbidden.intersection(data):
                raise ValueError("local workspace paths are not accepted")
        return data

    @field_validator("branch_name")
    @classmethod
    def reject_path_like_branch(cls, value: str | None) -> str | None:
        if value and (value.startswith("/") or "\\" in value):
            raise ValueError("branch name must not contain local paths")
        return value

    @field_validator("head_commit")
    @classmethod
    def normalize_commit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not all(character in "0123456789abcdef" for character in lowered):
            raise ValueError("head commit must be a git sha")
        return lowered
