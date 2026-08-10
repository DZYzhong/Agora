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
