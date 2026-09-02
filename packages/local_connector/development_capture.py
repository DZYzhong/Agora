"""Local Connector development-change capture.

Runs entirely in the client/CI execution plane and emits only bounded,
relative metadata: changed file paths with allowlisted statuses, a dirty
flag and diff-stat counters. It never emits diff bodies or file content,
and it never uploads the repository path.

The server validates and stores this structure without any filesystem
access. See PR1A Task 5B (docs/superpowers/plans/2026-08-28-agora-pr1a-runtime-mcp-hardening.md).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ALLOWED_STATUSES = ("added", "modified", "deleted", "renamed")
MAX_CHANGED_FILES = 500
MAX_PATH_BYTES = 512
_MAX_COUNTER = 1_000_000


def capture_local_development_change(
    *,
    workspace_root: str | Path | None = None,
    base_ref: str = "HEAD",
    head_ref: str | None = None,
) -> dict:
    """Capture a bounded development-change observation from the local repo.

    Returns:
        {
            "changed_files": [{"path": "<relative>", "status": "<allowlisted>"}],
            "dirty": bool,
            "diff_stat": {"files_changed": int, "insertions": int, "deletions": int},
        }
    """
    root = Path(workspace_root or os.environ.get("AGORA_WORKSPACE_ROOT") or os.getcwd())

    diff_args = [base_ref] + ([head_ref] if head_ref else [])
    name_status = _git(root, "diff", "--name-status", "--find-renames", *diff_args)
    numstat = _git(root, "diff", "--numstat", *diff_args)
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    porcelain = _git(root, "status", "--porcelain=v1")

    changed_files: list[dict] = []
    for raw_line in name_status.splitlines():
        parts = raw_line.split("\t")
        if len(parts) < 2:
            continue
        status = _status_label(parts[0])
        path = parts[-1]
        if status is None or not _bounded_path(path):
            continue
        changed_files.append({"path": path, "status": status})
        if len(changed_files) >= MAX_CHANGED_FILES:
            break

    for raw_line in untracked.splitlines():
        path = raw_line.strip()
        if not path or not _bounded_path(path):
            continue
        changed_files.append({"path": path, "status": "added"})
        if len(changed_files) >= MAX_CHANGED_FILES:
            break

    insertions = 0
    deletions = 0
    for raw_line in numstat.splitlines():
        parts = raw_line.split("\t")
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            insertions = min(insertions + int(parts[0]), _MAX_COUNTER)
            deletions = min(deletions + int(parts[1]), _MAX_COUNTER)

    return {
        "changed_files": changed_files,
        "dirty": bool(porcelain.strip()),
        "diff_stat": {
            "files_changed": len(changed_files),
            "insertions": insertions,
            "deletions": deletions,
        },
    }


def _status_label(raw_status: str) -> str | None:
    first = raw_status[0] if raw_status else ""
    mapping = {
        "A": "added",
        "M": "modified",
        "D": "deleted",
        "R": "renamed",
    }
    return mapping.get(first)


def _bounded_path(path: str) -> bool:
    if not path:
        return False
    if path.startswith("/") or "\\" in path:
        return False
    parts = path.split("/")
    if any(part in ("", "..", ".") for part in parts):
        return False
    if any(ord(character) < 32 for character in path):
        return False
    if "://" in path or " " in path or "\t" in path:
        return False
    return len(path.encode("utf-8")) <= MAX_PATH_BYTES


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout
