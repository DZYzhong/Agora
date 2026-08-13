from packages.domain.schemas import AssetCreate
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_context_retrieval_eval_covers_overview_source_memory_and_chunk_facts():
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    assets = {
        "overview_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="project_overview",
            source="agora",
            source_uri="agora://project-overview",
            title="Project Overview",
            content="Project overview modules include payments, kafka, and refund processing.",
        ),
        "code_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri="src/refund/service.py",
            title="service.py",
            content="class RefundService:\n    pass\n\nRefund retry idempotency implementation uses request keys.",
        ),
        "writeback_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="writeback",
            source="agent",
            source_uri="writebacks/kafka-risk",
            title="Kafka Risk Analysis",
            content="Kafka retry consistency risk can duplicate delivery when producer acknowledgements fail.",
        ),
        "doc_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="doc",
            source="git",
            source_uri="docs/refund.md",
            title="Refund Guide",
            content="Refund documentation explains retry handling and operator runbooks.",
        ),
    }
    for asset_id, asset in assets.items():
        keyword.index_asset(asset_id, asset)
        vector.index_asset(asset_id, asset)

    engine = ContextEngine(keyword_index=keyword, vector_index=vector)

    overview = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="analysis",
        query="介绍一下这个项目",
    )
    implementation = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund idempotency implementation",
    )
    risk = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="review",
        query="Kafka retry consistency risk",
    )

    assert overview.level == "overview"
    assert overview.source_refs[0]["asset_id"] == "overview_1"
    assert implementation.level == "source"
    assert implementation.source_refs[0]["asset_id"] == "code_1"
    assert implementation.source_refs[0]["chunk_id"] == "code_1:chunk:1"
    assert implementation.key_facts[0]["source_refs"] == ["code_1:chunk:1"]
    assert risk.level == "memory"
    assert risk.source_refs[0]["asset_id"] == "writeback_1"
