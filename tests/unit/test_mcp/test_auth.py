"""Token-auth logic tested DIRECTLY (E2) — the in-memory transport bypasses HTTP
bearer auth, so we exercise the StaticTokenVerifier/token map itself."""

from __future__ import annotations

import pytest

from cosmos77_ex06.mcp_servers.auth import build_verifier, token_map

from .conftest import COP_TOKEN, GOOD_TOKEN, THIEF_TOKEN


def test_token_map_role_and_orchestrator_scopes() -> None:
    """The orchestrator token carries every role scope; the role token only its own."""
    mapping = token_map("cop", COP_TOKEN, GOOD_TOKEN)
    assert mapping[COP_TOKEN]["scopes"] == ["read", "cop"]
    assert mapping[GOOD_TOKEN]["scopes"] == ["read", "cop", "thief"]
    assert mapping[GOOD_TOKEN]["client_id"] == "orchestrator"


async def test_good_token_accepted() -> None:
    """The orchestrator token verifies and carries the read scope."""
    verifier = build_verifier("cop")
    access = await verifier.verify_token(GOOD_TOKEN)
    assert access is not None
    assert "read" in access.scopes
    assert "cop" in access.scopes


async def test_role_token_accepted_with_role_scope() -> None:
    """The thief role token verifies on the thief server with the thief scope."""
    verifier = build_verifier("thief")
    access = await verifier.verify_token(THIEF_TOKEN)
    assert access is not None
    assert access.scopes == ["read", "thief"]


async def test_bad_token_rejected() -> None:
    """An unknown token is rejected (returns None)."""
    verifier = build_verifier("cop")
    assert await verifier.verify_token("not-a-real-token") is None


async def test_empty_token_rejected() -> None:
    """An empty token is rejected (returns None)."""
    verifier = build_verifier("thief")
    assert await verifier.verify_token("") is None


async def test_cross_role_token_absent_from_server_map() -> None:
    """The cop server's verifier does not accept the thief's role token."""
    verifier = build_verifier("cop")
    assert await verifier.verify_token(THIEF_TOKEN) is None


def test_build_verifier_unknown_role() -> None:
    """An unknown role is rejected at construction."""
    with pytest.raises(ValueError, match="unknown role"):
        build_verifier("warden")


async def test_unset_tokens_fall_back_to_random_and_reject_known_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No env tokens -> random fallbacks, so the server REJECTS every known token (never accepts blank)."""
    monkeypatch.delenv("COP_MCP_TOKEN", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_TOKEN", raising=False)
    verifier = build_verifier("cop")  # both tokens fall back to secrets.token_hex(32)
    assert (
        await verifier.verify_token(GOOD_TOKEN) is None
    )  # the real orchestrator token is NOT accepted
    assert await verifier.verify_token(COP_TOKEN) is None
    assert await verifier.verify_token("") is None
