"""Server-authoritative upload policy, revalidation and risk tiering.

Design: `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`
§7.2 — client sanitization is not the security boundary. The API revalidates
every upload (schema, path normalization, type, size, control characters,
secret patterns, policy version) and computes the risk tier from the actual
payload; a client can never self-report a downgrade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

POLICY_VERSION = "pr1c-1"

MAX_JSON_BODY_BYTES = 1_048_576  # 1 MiB default request body
MAX_AGENT_SUMMARY_BYTES = 8 * 1024
MAX_TEST_RESULT_BYTES = 8 * 1024
MAX_PATH_BYTES = 512
MAX_CHANGED_FILES = 500
MAX_SOURCE_ANCHORS = 200
MAX_CONTENT_BYTES = 64 * 1024
MAX_DIFF_STAT_JSON_BYTES = 4 * 1024

ALLOWED_UPLOAD_KINDS = frozenset(
    {
        "development_update",
        "context_proposal",
        "quality_evidence",
        "skill_candidate",
        "work_artifact_summary",
        "integration_signal",
    }
)

FORBIDDEN_PATH_PATTERN = re.compile(r"://|[\s]|[a-zA-Z][^/@\s]*:[^/@\s]*@")
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
CREDENTIAL_REMOTE_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+:[^@\s]+@")

SECRET_RULES = (
    "aws_access_key_id",
    "secret_access_key",
    "private_key",
    "-----BEGIN",
    "api[_-]?key",
    "bearer ",
    "password=",
    "token=",
)


class UploadTier(Enum):
    LOW = "low"
    HIGH = "high"


@dataclass(frozen=True)
class UploadAssessment:
    tier: UploadTier
    reasons: tuple[str, ...]
    policy_version: str = POLICY_VERSION

    @property
    def requires_grant(self) -> bool:
        return self.tier is UploadTier.HIGH


@dataclass(frozen=True)
class UploadPolicy:
    policy_version: str = POLICY_VERSION
    max_json_body_bytes: int = MAX_JSON_BODY_BYTES
    max_agent_summary_bytes: int = MAX_AGENT_SUMMARY_BYTES
    max_test_result_bytes: int = MAX_TEST_RESULT_BYTES
    max_path_bytes: int = MAX_PATH_BYTES
    max_changed_files: int = MAX_CHANGED_FILES
    max_source_anchors: int = MAX_SOURCE_ANCHORS
    max_content_bytes: int = MAX_CONTENT_BYTES
    max_diff_stat_json_bytes: int = MAX_DIFF_STAT_JSON_BYTES
    allowed_kinds: frozenset[str] = ALLOWED_UPLOAD_KINDS


def classify_upload(
    *,
    kind: str,
    has_source_excerpt: bool = False,
    secret_rule_exception: bool = False,
    forbidden_path_or_type: bool = False,
    over_default_limit: bool = False,
    policy_override: bool = False,
    quality_waiver: bool = False,
    policy_version: str = POLICY_VERSION,
) -> UploadAssessment:
    """Server-computed risk tier. Client claims never lower the tier."""
    reasons: list[str] = []
    if kind not in ALLOWED_UPLOAD_KINDS:
        reasons.append("unknown_payload_kind")
    if has_source_excerpt:
        reasons.append("source_or_document_excerpt")
    if secret_rule_exception:
        reasons.append("secret_rule_exception")
    if forbidden_path_or_type:
        reasons.append("forbidden_path_or_type")
    if over_default_limit:
        reasons.append("over_default_limit")
    if policy_override:
        reasons.append("policy_override")
    if quality_waiver:
        reasons.append("quality_waiver")
    tier = UploadTier.HIGH if reasons else UploadTier.LOW
    return UploadAssessment(tier=tier, reasons=tuple(reasons), policy_version=policy_version)


def revalidate_upload(
    *,
    kind: str,
    paths: list[str] | None = None,
    content: str | None = None,
    agent_summary: str | None = None,
    test_result: str | None = None,
    diff_stat_json: str | None = None,
    changed_files: int | None = None,
    source_anchors: int | None = None,
    policy: UploadPolicy | None = None,
) -> list[str]:
    """Return a list of policy violations; empty list means the upload is acceptable.

    Raises nothing: callers map violations to stable error codes.
    """
    policy = policy or UploadPolicy()
    violations: list[str] = []

    if kind not in policy.allowed_kinds:
        violations.append("unknown_payload_kind")

    for path in paths or []:
        violations.extend(revalidate_path(path, policy=policy))

    if content is not None and len(content.encode("utf-8")) > policy.max_content_bytes:
        violations.append("content_over_limit")
    if agent_summary is not None and len(agent_summary.encode("utf-8")) > policy.max_agent_summary_bytes:
        violations.append("agent_summary_over_limit")
    if test_result is not None and len(test_result.encode("utf-8")) > policy.max_test_result_bytes:
        violations.append("test_result_over_limit")
    if diff_stat_json is not None and len(diff_stat_json.encode("utf-8")) > policy.max_diff_stat_json_bytes:
        violations.append("diff_stat_over_limit")
    if changed_files is not None and changed_files > policy.max_changed_files:
        violations.append("changed_files_over_limit")
    if source_anchors is not None and source_anchors > policy.max_source_anchors:
        violations.append("source_anchors_over_limit")

    return violations


def revalidate_path(path: str, *, policy: UploadPolicy | None = None) -> list[str]:
    policy = policy or UploadPolicy()
    violations: list[str] = []
    if not path:
        violations.append("empty_path")
        return violations
    if path.startswith("/") or "\\" in path:
        violations.append("absolute_or_backslash_path")
    parts = path.split("/")
    if any(part in ("", "..", ".") for part in parts):
        violations.append("traversal_or_empty_segment")
    if CONTROL_CHARACTER_PATTERN.search(path):
        violations.append("control_character")
    if FORBIDDEN_PATH_PATTERN.search(path):
        violations.append("path_contains_credentials_or_secret_pattern")
    if len(path.encode("utf-8")) > policy.max_path_bytes:
        violations.append("path_over_limit")
    return violations


def revalidate_remote(remote: str | None) -> list[str]:
    if not remote:
        return []
    violations: list[str] = []
    if CREDENTIAL_REMOTE_PATTERN.search(remote) or "://" in remote and "@" in remote:
        violations.append("credentialized_remote")
    return violations


def contains_secret(value: str) -> bool:
    lowered = value.lower()
    return any(rule.lower() in lowered for rule in SECRET_RULES)


def redact_sensitive(text: str) -> str:
    """Redact credentials and secret-like values for logs and errors."""
    redacted = re.sub(CREDENTIAL_REMOTE_PATTERN, "****@", text)
    redacted = re.sub(r"(authorization:)[^\r\n]*", r"\1 ***REDACTED***", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(x-csrf-token:\s*)\S+", r"\1***REDACTED***", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(agora_session=)[^;\s]+", r"\1***REDACTED***", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(agora_csrf=)[^;\s]+", r"\1***REDACTED***", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(bearer\s+)[^\s]+", r"\1***REDACTED***", redacted, flags=re.IGNORECASE)
    return redacted
