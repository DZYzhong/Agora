from dataclasses import dataclass

from packages.core.services.mcp_tools import canonical_tool_names, deprecated_tool_map


HARNESS_PROTOCOL_CURRENT = "1.1"
HARNESS_PROTOCOL_SUPPORTED = ["1.0", "1.1"]
MCP_SERVER_NAME = "agora"
MCP_SERVER_VERSION = "0.1.0"
MINIMUM_LOCAL_CONNECTOR_VERSION = "0.1.0"
LEGACY_PROTOCOL_VERSION = "1.0"

# Derived from the canonical tool registry so advertisement and manifest
# cannot drift from the dispatch surface (see packages/core/services/mcp_tools.py).
CANONICAL_MCP_TOOLS = list(canonical_tool_names())

DEPRECATED_MCP_TOOLS = deprecated_tool_map()


@dataclass(frozen=True)
class ProtocolContext:
    protocol_version: str
    connector_version: str | None = None
    legacy: bool = False


class ProtocolNegotiationError(ValueError):
    def __init__(self, *, message: str, minimum_protocol_version: str | None = None):
        super().__init__(message)
        self.message = message
        self.minimum_protocol_version = minimum_protocol_version


def negotiate_protocol(
    protocol_version: str | None,
    *,
    connector_version: str | None = None,
) -> ProtocolContext:
    if connector_version and _version_tuple(connector_version) < _version_tuple(MINIMUM_LOCAL_CONNECTOR_VERSION):
        raise ProtocolNegotiationError(message=f"Agora Connector version {connector_version} is below the minimum supported version.")
    if not protocol_version:
        return ProtocolContext(protocol_version=LEGACY_PROTOCOL_VERSION, connector_version=connector_version, legacy=True)

    requested = protocol_version.strip()
    if requested not in HARNESS_PROTOCOL_SUPPORTED:
        raise ProtocolNegotiationError(message=f"Unsupported Agora protocol version: {requested}")
    return ProtocolContext(
        protocol_version=requested,
        connector_version=connector_version,
        legacy=requested == LEGACY_PROTOCOL_VERSION,
    )


def protocol_deprecation(context: ProtocolContext) -> dict | None:
    if not context.legacy:
        return None
    return {
        "legacy_protocol_version": LEGACY_PROTOCOL_VERSION,
        "current_protocol_version": HARNESS_PROTOCOL_CURRENT,
        "remove_after": "PR1A",
    }


def require_minimum_protocol(context: ProtocolContext, minimum_version: str) -> None:
    if _version_tuple(context.protocol_version) < _version_tuple(minimum_version):
        raise ProtocolNegotiationError(
            message=f"Agora protocol {minimum_version} or newer is required for this operation.",
            minimum_protocol_version=minimum_version,
        )


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


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
