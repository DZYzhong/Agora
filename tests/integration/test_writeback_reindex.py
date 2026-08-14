import inspect

from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_accepted_writeback_becomes_retrievable(fake_core):
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    service = MemoryWritebackService(core=fake_core)

    writeback = service.prepare_writeback(
        org_id="org_1",
        project_id="proj_1",
        session_id="sess_1",
        type="development_summary",
        title="Refund retry summary",
        content="Refund retry must cap retries and preserve idempotency.",
    )
    result = service.accept_writeback(writeback.id)

    assert keyword._assets == []
    assert vector._assets == []
    keyword.index_asset(result.pending_index.asset_id, result.pending_index.asset)
    vector.index_asset(result.pending_index.asset_id, result.pending_index.asset)

    context = ContextEngine(keyword_index=keyword, vector_index=vector).plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund retry idempotency",
        token_budget=1000,
    )

    assert "idempotency" in context.summary.lower()


def test_memory_writeback_service_has_no_direct_index_side_effect():
    assert ".index_asset(" not in inspect.getsource(MemoryWritebackService)
