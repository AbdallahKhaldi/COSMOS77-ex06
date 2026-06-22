"""The COP FastMCP server (E2/E3) — tools only, no LLM.

Exposes the shared communication + perception + action tools **plus** the cop-only
``place_barrier``, gated by a revocable ``StaticTokenVerifier`` (token from
``COP_MCP_TOKEN`` / ``ORCHESTRATOR_TOKEN``). Runnable as
``python -m cosmos77_ex06.mcp_servers.cop_server`` — HTTP on ``mcp.cop_port``.
"""

from __future__ import annotations

from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.mcp_servers.state_factory import make_state
from cosmos77_ex06.shared.config import Config

ROLE = "cop"
_config = Config()
_state = make_state(_config)
mcp = build_server(ROLE, _state, _config)


def main() -> None:  # pragma: no cover - HTTP boot, exercised by the live smoke test
    """Run the cop server over HTTP on the configured port."""
    host = str(_config.get("mcp.host", "0.0.0.0"))
    port = int(_config.get("mcp.cop_port"))
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
