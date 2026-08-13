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
    assert context.level == "module"
    assert context.source_refs[0]["asset_id"] == "asset_1"
    assert "refund" in context.summary.lower()
    assert context.source_refs[0]["preview"] == "Refund retry must be idempotent and capped."
    assert context.source_refs[0]["chunk_id"] == "asset_1:chunk:0"
    assert context.source_refs[0]["source_span"] == {
        "start_line": 1,
        "end_line": 1,
        "start_char": 0,
        "end_char": len(asset.content),
    }
    assert context.key_facts[0]["source_refs"] == ["asset_1:chunk:0"]


def test_context_engine_falls_back_to_project_overview_for_broad_queries():
    assets = [
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="doc",
            source="git",
            source_uri="pom.xml",
            title="pom.xml",
            content="<project><modules><module>df-new-rtdw</module></modules></project>",
        ),
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri="df-new-rtdw/src/main/java/TripDriverBehaviorsNevJob.java",
            title="df-new-rtdw/src/main/java/TripDriverBehaviorsNevJob.java",
            content="public class TripDriverBehaviorsNevJob {}",
        ),
    ]
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    for index, asset in enumerate(assets):
        keyword.index_asset(f"asset_{index}", asset)
        vector.index_asset(f"asset_{index}", asset)

    engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="analysis",
        query="核心模块 主要业务流程 潜在风险",
        token_budget=1000,
    )

    assert "No relevant project context found" not in context.summary
    assert context.source_refs
    assert "pom.xml" in context.summary


def test_context_engine_prefers_project_overview_for_broad_fallback():
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    keyword.index_asset(
        "file_1",
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri="src/refund/service.py",
            title="service.py",
            content="RefundService retries failed refunds.",
        ),
    )
    keyword.index_asset(
        "overview_1",
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="project_overview",
            source="agora",
            source_uri="agora://project-overview",
            title="Project Overview",
            content="Project overview with modules, dependencies, source paths, and tests.",
        ),
    )
    engine = ContextEngine(keyword_index=keyword, vector_index=vector)

    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="analysis",
        query="介绍一下这个项目",
    )

    assert context.source_refs[0]["title"] == "Project Overview"
    assert context.level == "overview"


def test_context_engine_prefers_project_overview_for_broad_query_even_with_matching_files():
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    assets = {
        "doc_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="doc",
            source="git",
            source_uri="docs/refund.md",
            title="docs/refund.md",
            content="# Refund Guide\n\n项目 retry handling and operator runbooks.",
        ),
        "code_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri="src/refund/service.py",
            title="src/refund/service.py",
            content="class RefundService:\n    pass\n\n项目 refund implementation uses request keys.",
        ),
        "overview_1": AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="project_overview",
            source="agora",
            source_uri="agora://project-overview",
            title="Project Overview",
            content="Project overview modules include src/refund and docs/refund.",
        ),
    }
    for asset_id, asset in assets.items():
        keyword.index_asset(asset_id, asset)
        vector.index_asset(asset_id, asset)
    engine = ContextEngine(keyword_index=keyword, vector_index=vector)

    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="analysis",
        query="介绍一下这个项目",
    )

    assert context.source_refs[0]["asset_id"] == "overview_1"
    assert context.level == "overview"


def test_context_engine_prefers_accepted_writeback_over_raw_code_matches():
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    for index in range(10):
        code_asset = AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri=f"src/KafkaProducer{index}.java",
            title=f"KafkaProducer{index}.java",
            content="package com.example; class KafkaProducer { FlinkKafkaProducer.Semantic.NONE; Kafka 输出一致性 }",
        )
        keyword.index_asset(f"code_{index}", code_asset)
        vector.index_asset(f"code_{index}", code_asset)
    writeback_asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="writeback",
        source="agent",
        source_uri="writebacks/analysis",
        title="Kafka consistency analysis",
        content="端到端一致性不足：多个 Kafka Producer 使用 FlinkKafkaProducer.Semantic.NONE。Kafka 输出仍可能重复或丢失。",
    )
    keyword.index_asset("writeback_1", writeback_asset)
    engine = ContextEngine(keyword_index=keyword, vector_index=vector)

    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="analysis",
        query="Kafka 输出一致性 FlinkKafkaProducer Semantic.NONE",
    )

    assert context.source_refs[0]["asset_id"] == "writeback_1"
    assert context.level == "memory"


def test_context_engine_boosts_sources_by_intent():
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    keyword.index_asset(
        "doc_1",
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="doc",
            source="git",
            source_uri="docs/kafka.md",
            title="Kafka Guide",
            content="Kafka retry behavior and consistency notes.",
        ),
    )
    keyword.index_asset(
        "code_1",
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="code_file",
            source="git",
            source_uri="src/kafka/producer.py",
            title="producer.py",
            content="Kafka retry behavior and consistency implementation.",
        ),
    )
    keyword.index_asset(
        "writeback_1",
        AssetCreate(
            org_id="org_1",
            project_id="proj_1",
            type="writeback",
            source="agent",
            source_uri="writebacks/kafka-risk",
            title="Kafka Risk Analysis",
            content="Kafka retry behavior and consistency risk analysis.",
        ),
    )
    engine = ContextEngine(keyword_index=keyword, vector_index=vector)

    implementation_context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="Kafka retry behavior consistency",
    )
    risk_context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="risk",
        query="Kafka retry behavior consistency",
    )

    assert implementation_context.source_refs[0]["asset_id"] == "code_1"
    assert risk_context.source_refs[0]["asset_id"] == "writeback_1"


def test_context_engine_source_ref_points_to_matching_chunk():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="docs/payments.md",
        title="Payment Notes",
        content="Payment overview stays stable.\n\nRefund retry uses idempotency keys.",
    )
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    keyword.index_asset("asset_1", asset)
    vector.index_asset("asset_1", asset)

    context = ContextEngine(keyword_index=keyword, vector_index=vector).plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund idempotency",
    )

    source = context.source_refs[0]
    assert source["chunk_id"] == "asset_1:chunk:1"
    assert source["source_span"] == {
        "start_line": 3,
        "end_line": 3,
        "start_char": asset.content.index("Refund"),
        "end_char": len(asset.content),
    }
    assert source["preview"] == "Refund retry uses idempotency keys."
