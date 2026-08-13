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
    assert context.source_refs[0]["preview"] == "Refund retry must be idempotent and capped."


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
