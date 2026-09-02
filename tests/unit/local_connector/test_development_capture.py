import subprocess

from packages.local_connector.development_capture import (
    MAX_CHANGED_FILES,
    capture_local_development_change,
)


def _run_git(repo_path, *args):
    subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)


def _init_repo(repo_path):
    repo_path.mkdir()
    _run_git(repo_path, "init")
    _run_git(repo_path, "config", "user.email", "dev@example.com")
    _run_git(repo_path, "config", "user.name", "Dev")


def test_capture_emits_bounded_relative_metadata(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('old')\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    (repo / "src" / "app.py").write_text("print('new')\nprint('more')\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test():\n    pass\n", encoding="utf-8")

    capture = capture_local_development_change(workspace_root=repo)

    paths = {entry["path"] for entry in capture["changed_files"]}
    assert paths == {"src/app.py", "tests/test_app.py"}
    statuses = {entry["status"] for entry in capture["changed_files"]}
    assert statuses <= {"added", "modified", "deleted", "renamed"}
    assert capture["dirty"] is True
    assert capture["diff_stat"]["files_changed"] == len(capture["changed_files"])
    assert capture["diff_stat"]["insertions"] >= 1
    for entry in capture["changed_files"]:
        assert not entry["path"].startswith("/")
        assert "\\" not in entry["path"]
        assert ".." not in entry["path"].split("/")


def test_capture_never_emits_diff_or_file_content(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "secret.txt").write_text("TOKEN=supersecretvalue\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    (repo / "secret.txt").write_text("TOKEN=rotated\n", encoding="utf-8")

    capture = capture_local_development_change(workspace_root=repo)

    serialized = str(capture)
    assert "TOKEN=" not in serialized
    assert "rotated" not in serialized
    assert "+TOKEN" not in serialized
    assert "-TOKEN" not in serialized


def test_capture_bounds_changed_file_count(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "base.py").write_text("base = 1\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    for index in range(MAX_CHANGED_FILES + 50):
        (repo / f"file_{index:04d}.py").write_text("x = 1\n", encoding="utf-8")
    _run_git(repo, "add", ".")

    capture = capture_local_development_change(workspace_root=repo)

    assert len(capture["changed_files"]) == MAX_CHANGED_FILES
    assert capture["diff_stat"]["files_changed"] == MAX_CHANGED_FILES


def test_capture_handles_non_git_directory(tmp_path):
    capture = capture_local_development_change(workspace_root=tmp_path)

    assert capture["changed_files"] == []
    assert capture["dirty"] is False
    assert capture["diff_stat"] == {"files_changed": 0, "insertions": 0, "deletions": 0}


def test_capture_reports_clean_workspace_as_not_dirty(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "ok.py").write_text("x = 1\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")

    capture = capture_local_development_change(workspace_root=repo)

    assert capture["changed_files"] == []
    assert capture["dirty"] is False
