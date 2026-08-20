from __future__ import annotations

import os
import subprocess
from pathlib import Path

from packages.domain.local_workspace import LocalWorkspaceObservation
from packages.local_connector.sanitization import normalize_repository_identity


def observe_git_workspace(workspace_root: str | Path | None = None) -> LocalWorkspaceObservation:
    root = Path(workspace_root or os.environ.get("AGORA_WORKSPACE_ROOT") or os.getcwd())
    remote = _git(root, "config", "--get", "remote.origin.url")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    head_commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain=v1")
    changed_count = 0
    untracked_count = 0
    for line in status.splitlines():
        if line.startswith("??"):
            untracked_count += 1
        elif line.strip():
            changed_count += 1
    return LocalWorkspaceObservation(
        repository=normalize_repository_identity(remote),
        branch_name=branch or None,
        head_commit=head_commit or None,
        dirty=bool(status.strip()),
        changed_file_count=changed_count,
        untracked_file_count=untracked_count,
    )


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()
