import pytest

from packages.harness.context_bundle import TokenBudgetTooSmall, build_context_bundle
from packages.knowledge.context_engine import PlannedContextPack


def _context_pack(*, summary: str = "Refund retry context.", sources: list[dict] | None = None) -> PlannedContextPack:
    return PlannedContextPack(
        id="ctx_1",
        org_id="org_1",
        project_id="proj_1",
        level="source",
        intent="implementation",
        summary=summary,
        key_facts=[{"fact": "Refund retry uses idempotency keys.", "source_refs": ["asset_1:chunk:0"]}],
        source_refs=sources
        if sources is not None
        else [
            {
                "asset_id": "asset_1",
                "asset_type": "code_file",
                "chunk_id": "asset_1:chunk:0",
                "title": "src/refund/service.py",
                "source_uri": "src/refund/service.py",
                "source_span": {"start_line": 1, "end_line": 20, "start_char": 0, "end_char": 500},
                "preview": "Refund retry source preview.",
                "relevance": 2.5,
                "retrieval_sources": ["keyword"],
            }
        ],
    )


def test_context_bundle_wraps_legacy_context_as_provisional_not_fresh():
    bundle = build_context_bundle(
        session_id="sess_1",
        query="refund retry",
        token_budget=1200,
        context_pack=_context_pack(),
    )

    assert bundle["protocol_version"] == "1.0"
    assert bundle["operation"] == "prepare_context"
    assert bundle["session_id"] == "sess_1"
    assert bundle["context_pack_id"] == "ctx_1"
    assert bundle["provisional"] is True
    assert bundle["freshness"] == {
        "repository_relation": "unknown",
        "workspace_state": "unknown",
        "context_coverage": "potentially_stale",
        "proposal_state": "none",
        "accepted_revision_id": None,
        "observed_commit_sha": None,
        "recommended_action": "use_provisional_context",
    }
    assert bundle["budget"]["estimated_tokens"] <= 1200
    assert bundle["source_refs"][0]["source_uri"] == "src/refund/service.py"


def test_context_bundle_missing_sources_recommends_local_analysis():
    bundle = build_context_bundle(
        session_id="sess_1",
        query="new project",
        token_budget=1000,
        context_pack=_context_pack(summary="No relevant project context found.", sources=[]),
    )

    assert bundle["freshness"]["context_coverage"] == "missing"
    assert bundle["freshness"]["recommended_action"] == "analyze_local_project"
    assert bundle["provisional"] is True


def test_context_bundle_returns_stable_budget_error_for_tiny_budget():
    with pytest.raises(TokenBudgetTooSmall) as exc:
        build_context_bundle(
            session_id="sess_1",
            query="refund retry",
            token_budget=5,
            context_pack=_context_pack(),
        )

    assert exc.value.code == "TOKEN_BUDGET_TOO_SMALL"
