"""Entry point for the live match console — ``cosmos77-pursuit serve`` / ``cosmos77-web``.

Reads ``web.host`` / ``web.port`` from config (``$PORT`` overrides for hosted deploys,
like the MCP servers), applies optional CLI overrides, and runs uvicorn. Mirrors
``mcp_servers.cop_server.main``.
"""

from __future__ import annotations

import os

from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.web.app import build_app


def main(
    host: str | None = None, port: int | None = None
) -> None:  # pragma: no cover - uvicorn boot
    """Run the console with uvicorn (CLI ``--host`` / ``--port`` override config)."""
    import uvicorn

    config = Config()
    bind_host = host or str(config.get("web.host", default="0.0.0.0"))
    bind_port = int(port or os.environ.get("PORT", config.get("web.port", default=8080)))
    uvicorn.run(build_app(config), host=bind_host, port=bind_port)


if __name__ == "__main__":  # pragma: no cover
    main()
