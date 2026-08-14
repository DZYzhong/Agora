from enum import Enum


class AssetType(str, Enum):
    CODE_FILE = "code_file"
    DOC = "doc"
    MODULE = "module"
    COMMIT = "commit"
    WRITEBACK = "writeback"


class AssetSource(str, Enum):
    GIT = "git"
    AGENT = "agent"
    MANUAL = "manual"


class SkillStatus(str, Enum):
    CANDIDATE = "candidate"
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class SessionStatus(str, Enum):
    STARTED = "started"
    CONTEXT_READY = "context_ready"
    WORKING = "working"
    REVIEWING = "reviewing"
    CLOSED = "closed"
    FAILED = "failed"


class WritebackStatus(str, Enum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class CredentialKind(str, Enum):
    HUMAN = "human"
    AGENT = "agent"


class ProjectRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"


class WorkItemStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class WorkItemStage(str, Enum):
    BACKLOG = "backlog"
    LEGACY_IMPORTED = "legacy_imported"


class WorkItemSource(str, Enum):
    MANUAL = "manual"
    LEGACY = "legacy"


class IdempotencyStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
