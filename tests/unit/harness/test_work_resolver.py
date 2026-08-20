from dataclasses import dataclass, field
from uuid import uuid4

from packages.harness.work_resolver import WorkResolver


@dataclass
class FakeProject:
    id: str = "project_1"
    org_id: str = "org_1"


@dataclass
class FakeWorkItem:
    org_id: str
    project_id: str
    title: str
    external_key: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


class FakeCore:
    def __init__(self):
        self.work_items: list[FakeWorkItem] = []

    def create_work_item(self, **kwargs):
        work_item = FakeWorkItem(**kwargs)
        self.work_items.append(work_item)
        return work_item

    def get_work_item_by_external_key(self, *, project_id: str, external_key: str):
        return next(
            (
                item
                for item in self.work_items
                if item.project_id == project_id and item.external_key == external_key
            ),
            None,
        )

    def find_work_items_by_title(self, *, project_id: str, title: str):
        needle = title.casefold()
        return [
            item
            for item in self.work_items
            if item.project_id == project_id and (needle in item.title.casefold() or item.title.casefold() in needle)
        ]


def test_explicit_external_key_reuses_project_work_item():
    core = FakeCore()
    existing = core.create_work_item(
        org_id="org_1",
        project_id="project_1",
        external_key="AG-128",
        title="实现支付状态流转",
    )

    result = WorkResolver(core).resolve(
        project=FakeProject(),
        user_message="帮我继续 AG-128",
    )

    assert result.next_action == "use_work_item"
    assert result.work_item.id == existing.id
    assert result.external_key == "AG-128"


def test_branch_hint_reuses_existing_work_item_when_message_has_no_task_id():
    core = FakeCore()
    existing = core.create_work_item(
        org_id="org_1",
        project_id="project_1",
        external_key="AG-777",
        title="补齐退款幂等保护",
    )

    result = WorkResolver(core).resolve(
        project=FakeProject(),
        user_message="实现当前分支的功能",
        branch_name="feature/AG-777-refund-idempotency",
    )

    assert result.next_action == "use_work_item"
    assert result.work_item.id == existing.id


def test_chinese_software_rd_title_creates_project_work_item():
    core = FakeCore()

    result = WorkResolver(core).resolve(
        project=FakeProject(),
        user_message="实现支付状态流转，补充回归测试",
    )

    assert result.next_action == "use_work_item"
    assert result.work_item.project_id == "project_1"
    assert result.work_item.org_id == "org_1"
    assert result.work_item.external_key is None
    assert result.work_item.title == "实现支付状态流转，补充回归测试"


def test_ambiguous_title_matches_ask_for_clarification_without_creating_work_item():
    core = FakeCore()
    core.create_work_item(org_id="org_1", project_id="project_1", title="支付状态流转")
    core.create_work_item(org_id="org_1", project_id="project_1", title="支付回调重试")

    result = WorkResolver(core).resolve(
        project=FakeProject(),
        user_message="继续支付任务",
    )

    assert result.next_action == "ask_user"
    assert result.work_item is None
    assert "支付状态流转" in result.clarification
    assert "支付回调重试" in result.clarification
    assert len(core.work_items) == 2
