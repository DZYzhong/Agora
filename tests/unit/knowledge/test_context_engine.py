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
