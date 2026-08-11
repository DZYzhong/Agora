import re
from dataclasses import dataclass


TASK_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


@dataclass(frozen=True)
class TaskResolution:
    task_id: str | None
    intent: str


class TaskResolver:
    def resolve(self, *, user_message: str) -> TaskResolution:
        match = TASK_ID_RE.search(user_message)
        return TaskResolution(task_id=match.group(0) if match else None, intent=_infer_intent(user_message))


def _infer_intent(message: str) -> str:
    lowered = message.lower()
    if "test" in lowered or "测试" in message:
        return "test_generation"
    if "review" in lowered or "风险" in message:
        return "review"
    return "implementation"
