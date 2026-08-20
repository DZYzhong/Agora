import subprocess

from packages.local_connector.git_observer import observe_git_workspace


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_git_observer_returns_sanitized_metadata_only(tmp_path):
    repo = tmp_path / "payment-service"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    _git(repo, "remote", "add", "origin", "https://alice:secret-token@git.example.cn/agora/payment-service.git")
    (repo / "service.py").write_text("TRACKED_SECRET = 'do not leak'\n")
    _git(repo, "add", "service.py")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "checkout", "-b", "feature/AG-128-context")
    (repo / "service.py").write_text("TRACKED_SECRET = 'changed but still private'\n")
    (repo / "notes.txt").write_text("UNTRACKED_SECRET should not leak\n")

    observation = observe_git_workspace(repo)
    encoded = observation.model_dump_json()

    assert observation.repository.normalized == "git.example.cn/agora/payment-service"
    assert observation.branch_name == "feature/AG-128-context"
    assert observation.head_commit
    assert observation.dirty is True
    assert observation.changed_file_count == 1
    assert observation.untracked_file_count == 1
    assert str(repo) not in encoded
    assert "alice" not in encoded
    assert "secret-token" not in encoded
    assert "TRACKED_SECRET" not in encoded
    assert "UNTRACKED_SECRET" not in encoded
