import pytest

from packages.harness.token_budget import (
    TokenBudgetTooSmall,
    estimate_tokens,
    stable_json_dumps,
    trim_payload_to_budget,
)


def test_stable_json_dumps_is_deterministic():
    left = {"b": 2, "a": {"z": 1, "m": [3, 2, 1]}}
    right = {"a": {"m": [3, 2, 1], "z": 1}, "b": 2}

    assert stable_json_dumps(left) == stable_json_dumps(right)


def test_trim_payload_drops_optional_facts_and_source_metadata_before_summary():
    payload = {
        "protocol_version": "1.0",
        "session_id": "sess_1",
        "summary": "S" * 900,
        "key_facts": [{"fact": f"fact-{index}", "source_refs": [f"asset_{index}:chunk:0"]} for index in range(20)],
        "source_refs": [
            {
                "asset_id": f"asset_{index}",
                "chunk_id": f"asset_{index}:chunk:0",
                "preview": "P" * 200,
                "source_span": {"start_line": 1, "end_line": 1, "start_char": 0, "end_char": 200},
                "retrieval_sources": ["keyword", "vector"],
            }
            for index in range(20)
        ],
        "budget": {},
    }

    budgeted = trim_payload_to_budget(payload, budget_limit=260)

    assert estimate_tokens(budgeted) <= 260
    assert budgeted["budget"]["budget_limit"] == 260
    assert budgeted["budget"]["estimated_tokens"] <= 260
    assert budgeted["budget"]["estimator_version"] == "chars_div_4_v1"
    assert budgeted["budget"]["truncation"]["key_facts_dropped"] > 0
    assert budgeted["budget"]["truncation"]["source_metadata_dropped"] > 0
    assert len(budgeted["summary"]) < 900


def test_trim_payload_raises_when_non_trimmable_envelope_exceeds_budget():
    with pytest.raises(TokenBudgetTooSmall):
        trim_payload_to_budget(
            {
                "protocol_version": "1.0",
                "session_id": "sess_1",
                "freshness": {"repository_relation": "unknown", "context_coverage": "missing"},
                "summary": "",
                "key_facts": [],
                "source_refs": [],
                "budget": {},
            },
            budget_limit=5,
        )
