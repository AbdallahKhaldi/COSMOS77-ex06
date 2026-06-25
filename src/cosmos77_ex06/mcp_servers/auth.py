"""Token authentication for the MCP servers (E2) — ``StaticTokenVerifier``.

Builds a revocable, env-sourced ``StaticTokenVerifier`` shared by both servers
(Rule 3, no duplication). Tokens map to required scopes; the orchestrator's bearer
token carries every role scope, while each role token carries only its own. No
secret ever appears in code or the repo (Rule 9) — values come from the env, and
rotating ``COP_MCP_TOKEN`` / ``THIEF_MCP_TOKEN`` revokes that role immediately.
"""

from __future__ import annotations

import os
import secrets
from typing import Any

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

ROLE_ENV = {"cop": "COP_MCP_TOKEN", "thief": "THIEF_MCP_TOKEN"}
ORCH_ENV = "ORCHESTRATOR_TOKEN"
READ_SCOPE = "read"


def token_map(role: str, role_token: str, orch_token: str) -> dict[str, dict[str, Any]]:
    """Return the ``StaticTokenVerifier`` token→claims map for ``role``.

    The role token gets ``["read", role]``; the orchestrator token gets every role
    scope so the single client may drive both servers. Kept pure for direct
    unit-testing of the token/scope logic without a network.
    """
    return {
        role_token: {"client_id": role, "scopes": [READ_SCOPE, role]},
        orch_token: {"client_id": "orchestrator", "scopes": [READ_SCOPE, "cop", "thief"]},
    }


def build_verifier(role: str) -> StaticTokenVerifier:
    """Build a static-token verifier for ``role`` from env tokens (no secrets in code).

    Reads ``COP_MCP_TOKEN`` / ``THIEF_MCP_TOKEN`` and ``ORCHESTRATOR_TOKEN`` from the
    environment. When a token is ABSENT — e.g. a cloud platform's build-time
    ``fastmcp inspect`` runs before runtime secrets are injected — it falls back to a
    fresh unguessable random token so the module import never crashes (the real env
    tokens are read again when the server actually boots at runtime). A genuinely unset
    token therefore yields a server that safely REJECTS every call, never one that
    crashes the build or accepts a blank/known token.
    """
    if role not in ROLE_ENV:
        raise ValueError(f"unknown role: {role!r}")
    role_token = os.environ.get(ROLE_ENV[role]) or secrets.token_hex(32)
    orch_token = os.environ.get(ORCH_ENV) or secrets.token_hex(32)
    return StaticTokenVerifier(
        tokens=token_map(role, role_token, orch_token),
        required_scopes=[READ_SCOPE],
    )
