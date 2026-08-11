from packages.domain.schemas import AssetCreate
from packages.knowledge.chunking import chunk_asset
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_chunk_asset_splits_content_with_source_metadata():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Payment service\n\nRefund module handles refund retry.",
    )

    chunks = chunk_asset(asset)

    assert chunks
    assert chunks[0].source_uri == "README.md"


def test_fake_indexes_return_project_scoped_results():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Refund retry policy",
    )
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()

    keyword.index_asset(asset_id="asset_1", asset=asset)
    vector.index_asset(asset_id="asset_1", asset=asset)

    assert keyword.search(org_id="org_1", project_id="proj_1", query="refund")
    assert vector.search(org_id="org_1", project_id="proj_1", query="retry")
