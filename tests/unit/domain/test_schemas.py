from packages.domain.enums import AssetType, WritebackStatus
from packages.domain.schemas import ProjectCreate, WritebackCreate


def test_project_create_requires_name_and_org():
    payload = ProjectCreate(org_id="org_1", name="Payment", slug="payment")

    assert payload.org_id == "org_1"
    assert payload.slug == "payment"


def test_writeback_defaults_to_draft():
    payload = WritebackCreate(
        org_id="org_1",
        project_id="proj_1",
        type="development_summary",
        title="AG-128 summary",
        content="Implemented refund retry.",
    )

    assert payload.status == WritebackStatus.DRAFT
    assert payload.type == "development_summary"


def test_asset_type_contains_code_file():
    assert AssetType.CODE_FILE == "code_file"
