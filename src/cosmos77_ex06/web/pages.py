"""Page handlers for the live console — the index + the public challenger briefing.

Kept out of routes.py (which holds the JSON/SSE API) so each file stays small and the
'page vs api' split is explicit. Both pages are public (no passphrase needed to VIEW);
the run endpoint is where the gate lives.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request


async def index(request: Request) -> Any:
    """Serve the single-page console (no passphrase needed to VIEW)."""
    return request.app.state.templates.TemplateResponse(request, "index.html")


async def challenge(request: Request) -> Any:
    """Serve the public challenger briefing — how to play / challenge COSMOS77 (E12).

    The cop/thief URLs + console link are rendered from live config (never hardcoded), so
    the page a challenger lands on always advertises our current MCP endpoints.
    """
    cfg = request.app.state.config
    console = str(cfg.get("web.public_url", default="")) or str(request.base_url).rstrip("/")
    ctx = {
        "cop_url": str(cfg.get("mcp.cop_url", default="")),
        "thief_url": str(cfg.get("mcp.thief_url", default="")),
        "console_url": console,
    }
    return request.app.state.templates.TemplateResponse(request, "challenge.html", ctx)
