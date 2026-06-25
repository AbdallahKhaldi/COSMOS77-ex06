"""Standalone request_move server for the NajAmjad bonus — exposes OUR move oracle (E12).

A tiny FastMCP server (one per role) exposing the single tool NajAmjad's orchestrator calls:
``request_move(observation, auth_token) -> "[INTENT: ...] prose"``. The ``auth_token`` is checked
against our per-role bonus token (``OUR_BONUS_<ROLE>_TOKEN`` in the gitignored env); a mismatch
returns a safe HOLD and reveals nothing. Kept SEPARATE from our prof-submission servers (which keep
the tools-only contract). Deterministic, no LLM. Run one per role and expose over public HTTPS; the
two module-level ``cop_mcp`` / ``thief_mcp`` objects are the deploy entry points.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP

from cosmos77_ex06.bonus import oracle
from cosmos77_ex06.shared.config import Config

_UNAUTH = "[INTENT: HOLD] unauthorized"


def build(role: str, config: Config | None = None) -> FastMCP:
    """Build the bonus ``request_move`` server for ``role`` (``cop``|``thief``); token from env."""
    cfg = config or Config()
    token = os.environ.get(f"OUR_BONUS_{role.upper()}_TOKEN", "")
    mcp: FastMCP = FastMCP(f"cosmos77-bonus-{role}")

    @mcp.tool
    def request_move(observation: dict[str, Any], auth_token: str) -> str:
        """Return our deterministic move for ``observation`` (the NajAmjad bonus contract)."""
        if not token or auth_token != token:
            return _UNAUTH
        return oracle.decide(observation, cfg)

    return mcp


cop_mcp = build("cop")
thief_mcp = build("thief")
