from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class DevelopmentChangeSummary:
    title: str
    content: str


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    category: str


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
        sections.append(f"## 功能变更\n{agent_summary.strip()}")
    elif session_intent:
        sections.append(f"## 功能变更\n本次开发任务：{session_intent.strip()}")

    if repo_path:
        changed_files, diff = _collect_git_diff(Path(repo_path), base_ref=base_ref, head_ref=head_ref)
        sections.append(_format_impact(changed_files))
        sections.append(diff)

    if test_result:
        sections.append(f"## 测试结果\n{test_result.strip()}")
    elif repo_path:
        sections.append("## 测试结果\nAgent 未提供测试结果，请审核时确认是否已完成必要验证。")

    if repo_path:
        sections.append(_format_risks(changed_files if "changed_files" in locals() else []))

    if not sections:
        sections.append("## 功能变更\n本次会话已关闭，但 Agent 未提供变更摘要或仓库 diff。")

    sections.append("## 审核建议\n请确认以上变更描述、影响文件和测试结果准确后再 Accept 入库。")
    return DevelopmentChangeSummary(title=title, content="\n\n".join(sections))


def _collect_git_diff(repo_path: Path, *, base_ref: str, head_ref: str | None) -> tuple[list[ChangedFile], str]:
    if not repo_path.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
    if not (repo_path / ".git").exists():
        raise ValueError(f"Repository path is not a git repository: {repo_path}")

    diff_args = [base_ref, head_ref] if head_ref else [base_ref]
    name_status = _git(repo_path, ["diff", "--name-status", "--find-renames", *diff_args])
    stat = _git(repo_path, ["diff", "--stat", *diff_args])
    untracked = _git(repo_path, ["ls-files", "--others", "--exclude-standard"])

    changed_files = _parse_changed_files(name_status, untracked)
    changed_files_text = _format_changed_files(changed_files)
    if not changed_files_text:
        changed_files_text = "未发现相对目标版本的代码差异。"
    if not stat.strip():
        stat = "无 diff 统计。"

    return (
        changed_files,
        "\n".join(
            [
                "## Git Diff 摘要",
                f"- 仓库路径：`{repo_path}`",
                f"- 对比范围：`{base_ref}`" + (f" -> `{head_ref}`" if head_ref else " -> 工作区"),
                "",
                "### 影响文件",
                changed_files_text,
                "",
                "### 变更统计",
                f"```text\n{stat.strip()}\n```",
            ]
        ),
    )


def _parse_changed_files(name_status: str, untracked: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    for raw_line in name_status.splitlines():
        parts = raw_line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1]
        files.append(ChangedFile(path=path, status=_status_label(status), category=_category(path)))
    for raw_line in untracked.splitlines():
        path = raw_line.strip()
        if path:
            files.append(ChangedFile(path=path, status="新增", category=_category(path)))
    return files


def _format_impact(files: list[ChangedFile]) -> str:
    if not files:
        return "## 影响范围\n未发现相对目标版本的代码差异。"
    lines = ["## 影响范围"]
    for category in ("源码", "测试", "配置", "文档", "其他"):
        for file in files:
            if file.category == category:
                lines.append(f"- {category}：`{file.path}` ({file.status})")
    return "\n".join(lines)


def _format_changed_files(files: list[ChangedFile]) -> str:
    return "\n".join(f"- `{file.path}` ({file.status})" for file in files)


def _format_risks(files: list[ChangedFile]) -> str:
    risks = []
    categories = {file.category for file in files}
    if "配置" in categories:
        risks.append("- 配置文件发生变化，请确认环境差异、密钥、连接地址和默认值不会影响生产。")
    if "源码" in categories and "测试" not in categories:
        risks.append("- 源码发生变化但未检测到测试文件变更，请确认已有测试或补充回归测试。")
    if not risks:
        risks.append("- 未识别到明显结构性风险，仍需审核业务语义和测试充分性。")
    return "## 风险与注意事项\n" + "\n".join(risks)


def _category(path: str) -> str:
    lower = path.lower()
    if lower.startswith("tests/") or "/tests/" in lower or lower.startswith("src/test/") or lower.endswith(("_test.py", ".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx")):
        return "测试"
    if lower.endswith((".yml", ".yaml", ".properties", ".env", ".json", ".toml", ".ini")):
        return "配置"
    if lower.endswith((".md", ".rst", ".txt")):
        return "文档"
    if lower.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".kt", ".scala", ".xml")):
        return "源码"
    return "其他"


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
