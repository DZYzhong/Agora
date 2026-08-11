from packages.domain.schemas import AssetCreate
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_context_engine_generates_traceable_context_pack():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="docs/refund.md",
        title="Refund Design",
        content="Refund retry must be idempotent and capped.",
    )
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    keyword.index_asset("asset_1", asset)
    vector.index_asset("asset_1", asset)

    engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund retry",
        token_budget=1000,
    )

    assert context.summary
    assert context.source_refs[0]["asset_id"] == "asset_1"
    assert "refund" in context.summary.lower()
