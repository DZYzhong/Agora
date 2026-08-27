HARNESS_PROTOCOL_CURRENT = "1.0"
HARNESS_PROTOCOL_SUPPORTED = ["1.0"]
MCP_SERVER_NAME = "agora"
MCP_SERVER_VERSION = "0.1.0"
MINIMUM_LOCAL_CONNECTOR_VERSION = "0.1.0"

CANONICAL_MCP_TOOLS = [
    "agora_start_work",
    "agora_prepare_context",
    "agora_fetch_context_ref",
    "agora_submit_context_proposal",
    "agora_submit_skill_candidate",
    "agora_suggest_skills",
    "agora_record_evidence",
    "agora_get_quality_status",
    "agora_get_project_status",
    "agora_get_protocol_manifest",
    "agora_close_work",
]

DEPRECATED_MCP_TOOLS = {
    "agora_plan_context": {
        "canonical_tool": "agora_prepare_context",
        "remove_after": "P2",
    },
    "agora_record_event": {
        "canonical_tool": None,
        "remove_after": "P2",
    },
    "agora_prepare_writeback": {
        "canonical_tool": None,
        "remove_after": "P2",
    },
    "agora_search_knowledge": {
        "canonical_tool": "agora_prepare_context",
        "remove_after": "P2",
    },
}


def build_protocol_manifest() -> dict:
    return {
        "format": "agora-protocol-manifest/v1",
        "mcp_server": {
            "name": MCP_SERVER_NAME,
            "version": MCP_SERVER_VERSION,
        },
        "harness_protocol": {
            "current": HARNESS_PROTOCOL_CURRENT,
            "supported": HARNESS_PROTOCOL_SUPPORTED,
        },
        "tools": {
            "canonical": CANONICAL_MCP_TOOLS,
            "deprecated": DEPRECATED_MCP_TOOLS,
        },
        "compatibility": {
            "minimum_local_connector_version": MINIMUM_LOCAL_CONNECTOR_VERSION,
            "requires_request_id_header": True,
            "requires_idempotency_keys": True,
            "local_paths_never_uploaded_by_default": True,
        },
    }
