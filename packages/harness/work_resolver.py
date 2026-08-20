import re
from dataclasses import dataclass

from packages.harness.task_resolver import TASK_ID_RE, infer_intent

BRANCH_TASK_ID_RE = re.compile(r"(?:^|[/_-])([A-Z][A-Z0-9]+-\d+)(?:$|[/_-])")


@dataclass(frozen=True)
class WorkResolution:
    work_item: object | None
    external_key: str | None
    title: str | None
    intent: str
    next_action: str
    clarification: str | None = None


class WorkResolver:
    def __init__(self, core):
        self.core = core

    def resolve(self, *, project, user_message: str, branch_name: str | None = None) -> WorkResolution:
        intent = infer_intent(user_message)
        external_key = _extract_external_key(user_message) or _extract_external_key(branch_name or "")
        title = _extract_title(user_message=user_message, external_key=external_key)

        if external_key:
            existing = self.core.get_work_item_by_external_key(project_id=project.id, external_key=external_key)
            if existing is not None:
                return WorkResolution(existing, external_key, existing.title, intent, "use_work_item")
            work_item = self.core.create_work_item(
                org_id=project.org_id,
                project_id=project.id,
                external_key=external_key,
                title=title or external_key,
            )
            return WorkResolution(work_item, external_key, work_item.title, intent, "use_work_item")

        if _needs_title(user_message):
            return WorkResolution(
                None,
                None,
                None,
                intent,
                "ask_user",
                "请提供要开始的工作项标题或任务编号。",
            )

        matches = self.core.find_work_items_by_title(project_id=project.id, title=title)
        if len(matches) == 1:
            match = matches[0]
            return WorkResolution(match, match.external_key, match.title, intent, "use_work_item")
        if len(matches) > 1:
            options = "、".join(item.title for item in matches[:5])
            return WorkResolution(
                None,
                None,
                title,
                intent,
                "ask_user",
                f"找到多个可能的工作项：{options}。请提供任务编号或更精确的标题。",
            )

        work_item = self.core.create_work_item(
            org_id=project.org_id,
            project_id=project.id,
            title=title,
        )
        return WorkResolution(work_item, None, work_item.title, intent, "use_work_item")


def _extract_external_key(text: str) -> str | None:
    task_match = TASK_ID_RE.search(text)
    if task_match:
        return task_match.group(0)
    branch_match = BRANCH_TASK_ID_RE.search(text)
    return branch_match.group(1) if branch_match else None


def _extract_title(*, user_message: str, external_key: str | None) -> str:
    title = user_message.strip()
    if external_key:
        title = title.replace(external_key, "", 1)
    title = re.sub(r"^\s*(帮我|请|继续|开始|处理|做|基于 Agora)?\s*(做|处理|继续)?\s*", "", title)
    title = title.strip(" ：:，,.-")
    title = re.sub(r"^(这个|当前)?\s*任务[:：]?", "", title).strip(" ：:，,.-")
    title = re.sub(r"(这个|当前)?任务$", "", title).strip(" ：:，,.-")
    return title or user_message.strip()


def _needs_title(user_message: str) -> bool:
    stripped = user_message.strip()
    vague_messages = {"继续任务", "继续这个任务", "开始工作", "处理任务", "做任务", "继续当前任务"}
    return stripped in vague_messages
