from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class DevelopmentChangeSummary:
    title: str
    content: str


def capture_development_change(
    *,
    repo_path: str | None = None,
    base_ref: str = "HEAD",
    head_ref: str | None = None,
    agent_summary: str | None = None,
    test_result: str | None = None,
    session_intent: str | None = None,
) -> DevelopmentChangeSummary:
    sections: list[str] = []
    title_seed = agent_summary or session_intent or "开发变更"
    title = _title_from_summary(title_seed)

    if agent_summary:
        sections.append(f"## 变更总结\n{agent_summary.strip()}")
    elif session_intent:
        sections.append(f"## 变更总结\n本次开发任务：{session_intent.strip()}")

    if repo_path:
        diff = _collect_git_diff(Path(repo_path), base_ref=base_ref, head_ref=head_ref)
        sections.append(diff)

    if test_result:
        sections.append(f"## 测试结果\n{test_result.strip()}")

    if not sections:
        sections.append("## 变更总结\n本次会话已关闭，但 Agent 未提供变更摘要或仓库 diff。")

    sections.append("## 审核建议\n请确认以上变更描述、影响文件和测试结果准确后再 Accept 入库。")
    return DevelopmentChangeSummary(title=title, content="\n\n".join(sections))


def _collect_git_diff(repo_path: Path, *, base_ref: str, head_ref: str | None) -> str:
    if not repo_path.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
    if not (repo_path / ".git").exists():
        raise ValueError(f"Repository path is not a git repository: {repo_path}")

    diff_args = [base_ref, head_ref] if head_ref else [base_ref]
    name_status = _git(repo_path, ["diff", "--name-status", "--find-renames", *diff_args])
    stat = _git(repo_path, ["diff", "--stat", *diff_args])

    changed_files = _format_changed_files(name_status)
    if not changed_files:
        changed_files = "未发现相对目标版本的代码差异。"
    if not stat.strip():
        stat = "无 diff 统计。"

    return "\n".join(
        [
            "## Git Diff 摘要",
            f"- 仓库路径：`{repo_path}`",
            f"- 对比范围：`{base_ref}`" + (f" -> `{head_ref}`" if head_ref else " -> 工作区"),
            "",
            "### 影响文件",
            changed_files,
            "",
            "### 变更统计",
            f"```text\n{stat.strip()}\n```",
        ]
    )


def _format_changed_files(name_status: str) -> str:
    lines = []
    for raw_line in name_status.splitlines():
        parts = raw_line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1]
        lines.append(f"- `{path}` ({_status_label(status)})")
    return "\n".join(lines)


def _status_label(status: str) -> str:
    if status.startswith("A"):
        return "新增"
    if status.startswith("M"):
        return "修改"
    if status.startswith("D"):
        return "删除"
    if status.startswith("R"):
        return "重命名"
    return status


def _title_from_summary(summary: str) -> str:
    normalized = " ".join(summary.split())
    if len(normalized) <= 40:
        return normalized
    return f"{normalized[:40]}..."


def _git(repo_path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
