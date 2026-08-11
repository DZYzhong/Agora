from pathlib import Path
import subprocess


class GitCloneError(RuntimeError):
    pass


def clone_repository(remote: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", remote, str(target_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitCloneError(detail or f"git clone failed with exit code {result.returncode}")
