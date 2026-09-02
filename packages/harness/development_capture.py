from dataclasses import dataclass
from pathlib import Path
import subprocess

from packages.local_connector.development_capture import ALLOWED_STATUSES


@dataclass(frozen=True)
class DevelopmentChangeSummary:
    title: str
    content: str
    structured: dict


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    category: str


def capture_development_change(
    *,
    agent_summary: str | None = None,
    test_result: str | None = None,
    session_intent: str | None = None,
    changed_files: list[dict] | None = None,
    dirty: bool = False,
    diff_stat: dict | None = None,
    repo_path: str | None = None,
    base_ref: str = "HEAD",
    head_ref: str | None = None,
) -> DevelopmentChangeSummary:
    """Build a development-update summary.

    Two capture paths:

    - Structured (default): `changed_files`/`dirty`/`diff_stat` come from the
      Local Connector and are already validated server-side; no filesystem
      access happens here.
    - Legacy: `repo_path` triggers a server-side `git diff`. This is the
      deprecated 1.0 behavior and is only reachable through the API's
      explicit root-containment gate in development/test environments.
    """
    sections: list[str] = []
    title_seed = agent_summary or session_intent or "开发变更"
    title = _title_from_summary(title_seed)
    files: list[ChangedFile] = []

    if agent_summary:
        sections.append(f"## 功能变更\n{agent_summary.strip()}")
    elif session_intent:
        sections.append(f"## 功能变更\n本次开发任务：{session_intent.strip()}")

    if repo_path:
        files, diff = _collect_git_diff(Path(repo_path), base_ref=base_ref, head_ref=head_ref)
        sections.append(_format_impact(files))
        sections.append(diff)
    elif changed_files:
        files = _files_from_structured(changed_files)
        sections.append(_format_impact(files))
        sections.append(_format_diff_stat(diff_stat or {}, dirty=dirty))

    if test_result:
        sections.append(f"## 测试结果\n{test_result.strip()}")
    elif repo_path or changed_files:
        sections.append("## 测试结果\nAgent 未提供测试结果，请审核时确认是否已完成必要验证。")

    risks = _risk_items(files) if (repo_path or changed_files) else []
    if repo_path or changed_files:
        sections.append("## 风险与注意事项\n" + "\n".join(f"- {risk}" for risk in risks))

    if not sections:
        sections.append("## 功能变更\n本次会话已关闭，但 Agent 未提供变更摘要或仓库 diff。")

    follow_ups = ["请确认以上变更描述、影响文件和测试结果准确后再 Accept 入库。"]
    sections.append("## 审核建议\n" + "\n".join(f"- {item}" for item in follow_ups))
    return DevelopmentChangeSummary(
        title=title,
        content="\n\n".join(sections),
        structured={
            "summary": (agent_summary or f"本次开发任务：{session_intent}" if session_intent else "本次会话已关闭，但 Agent 未提供变更摘要。").strip(),
            "changed_files": [
                {"path": file.path, "status": _english_status(file.status), "category": file.category}
                for file in files
            ],
            "tests": _parse_test_result(test_result),
            "risks": risks,
            "follow_ups": follow_ups,
        },
    )


def _files_from_structured(changed_files: list[dict]) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    for item in changed_files:
        path = item.get("path", "")
        status = item.get("status", "modified")
        if status not in ALLOWED_STATUSES:
            status = "modified"
        files.append(
            ChangedFile(
                path=path,
                status=_status_display(status),
                category=_category(path),
            )
        )
    return files


def _format_diff_stat(diff_stat: dict, *, dirty: bool) -> str:
    files = int(diff_stat.get("files_changed", 0))
    insertions = int(diff_stat.get("insertions", 0))
    deletions = int(diff_stat.get("deletions", 0))
    lines = [
        "## Git Diff 摘要",
        f"- 变更文件数：{files}",
        f"- 新增行：+{insertions}，删除行：-{deletions}",
        f"- 工作区状态：{'有未提交变更' if dirty else '干净'}",
    ]
    if not files:
        lines.append("- 未发现相对目标版本的代码差异。")
    return "\n".join(lines)


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
    return "## 风险与注意事项\n" + "\n".join(f"- {risk}" for risk in _risk_items(files))


def _risk_items(files: list[ChangedFile]) -> list[str]:
    risks = []
    categories = {file.category for file in files}
    if "配置" in categories:
        risks.append("配置文件发生变化，请确认环境差异、密钥、连接地址和默认值不会影响生产。")
    if "源码" in categories and "测试" not in categories:
        risks.append("源码发生变化但未检测到测试文件变更，请确认已有测试或补充回归测试。")
    if not risks:
        risks.append("未识别到明显结构性风险，仍需审核业务语义和测试充分性。")
    return risks


def _parse_test_result(test_result: str | None) -> list[dict]:
    if not test_result:
        return []
    raw = test_result.strip()
    lowered = raw.lower()
    status = "passed" if "pass" in lowered or "通过" in raw else "failed" if "fail" in lowered or "失败" in raw else "unknown"
    command = raw
    for separator in (" - ", "：", ":"):
        if separator in raw:
            command = raw.split(separator, 1)[0].strip()
            break
    return [{"command": command, "status": status, "raw": raw}]


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


def _status_display(status: str) -> str:
    mapping = {
        "added": "新增",
        "modified": "修改",
        "deleted": "删除",
        "renamed": "重命名",
    }
    return mapping.get(status, status)


def _english_status(status: str) -> str:
    mapping = {
        "新增": "added",
        "修改": "modified",
        "删除": "deleted",
        "重命名": "renamed",
    }
    return mapping.get(status, status)


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
