from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_accepted_writeback_becomes_retrievable(fake_core):
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    service = MemoryWritebackService(core=fake_core, keyword_index=keyword, vector_index=vector)

    writeback = service.prepare_writeback(
        org_id="org_1",
        project_id="proj_1",
        session_id="sess_1",
        type="development_summary",
        title="Refund retry summary",
        content="Refund retry must cap retries and preserve idempotency.",
    )
    service.accept_writeback(writeback.id)

    context = ContextEngine(keyword_index=keyword, vector_index=vector).plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund retry idempotency",
        token_budget=1000,
    )

    assert "idempotency" in context.summary.lower()
