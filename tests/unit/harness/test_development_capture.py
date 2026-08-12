import subprocess

from packages.harness.development_capture import capture_development_change


def _run_git(repo_path, *args):
    subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)


def test_capture_development_change_structures_summary_impact_tests_and_risks(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _run_git(repo_path, "init")
    _run_git(repo_path, "config", "user.email", "dev@example.com")
    _run_git(repo_path, "config", "user.name", "Dev")
    (repo_path / "src").mkdir()
    (repo_path / "src" / "payment.py").write_text("def pay():\n    return 'old'\n", encoding="utf-8")
    _run_git(repo_path, "add", ".")
    _run_git(repo_path, "commit", "-m", "initial")

    (repo_path / "src" / "payment.py").write_text("def pay():\n    return 'new'\n", encoding="utf-8")
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_payment.py").write_text("def test_pay():\n    assert True\n", encoding="utf-8")
    (repo_path / "config.yml").write_text("payment:\n  enabled: true\n", encoding="utf-8")

    summary = capture_development_change(
        repo_path=str(repo_path),
        agent_summary="实现支付状态流转，并补充支付回归测试。",
        test_result="pytest tests/test_payment.py passed",
    )

    assert "## 功能变更" in summary.content
    assert "实现支付状态流转" in summary.content
    assert "## 影响范围" in summary.content
    assert "- 源码：`src/payment.py` (修改)" in summary.content
    assert "- 测试：`tests/test_payment.py` (新增)" in summary.content
    assert "- 配置：`config.yml` (新增)" in summary.content
    assert "## 测试结果" in summary.content
    assert "pytest tests/test_payment.py passed" in summary.content
    assert "## 风险与注意事项" in summary.content
    assert "配置文件发生变化" in summary.content
