"""ASGI entrypoints for cloud / uvicorn deployment (PRD §7, E6).

Each server exposes a standard ASGI application via FastMCP's ``http_app()`` so it
can be hosted on Prefect Horizon / FastMCP Cloud or run behind uvicorn + a tunnel::

    uvicorn cosmos77_ex06.mcp_servers.app:cop_app   --host 0.0.0.0 --port 8001
    uvicorn cosmos77_ex06.mcp_servers.app:thief_app --host 0.0.0.0 --port 8002

Importing this module builds both servers, which requires the MCP token env vars
to be present (Rule 9 — secrets from the environment, never the repo).
"""

from __future__ import annotations

from cosmos77_ex06.mcp_servers.cop_server import mcp as cop_mcp
from cosmos77_ex06.mcp_servers.thief_server import mcp as thief_mcp

cop_app = cop_mcp.http_app()  # ASGI app, mounted at /mcp  # pragma: no cover
thief_app = thief_mcp.http_app()  # ASGI app, mounted at /mcp  # pragma: no cover
