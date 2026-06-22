"""Auth gate for sync_state + the no-hardcoded-URL guard (E2/E6/E8).

``sync_state`` / ``get_full_state`` must be ORCHESTRATOR-ONLY (they overwrite / expose
ground truth). The in-memory transport bypasses HTTP bearer auth, so — as in
``test_mcp/test_auth`` — we exercise the ``_assert_orchestrator`` gate directly by
faking the access token. We also assert no MCP URL literal is hardcoded in ``src/``
(promotion local->cloud is a config edit only, E8 / PRD §5).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import cosmos77_ex06 as pkg
from cosmos77_ex06.mcp_servers import server


def _fake_token(scopes: list[str]) -> SimpleNamespace:
    """A minimal access-token stand-in carrying ``scopes`` (matches FastMCP's shape)."""
    return SimpleNamespace(scopes=scopes, client_id="x")


def test_orchestrator_gate_accepts_both_role_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A token carrying BOTH cop+thief scopes (the orchestrator) passes the gate."""
    monkeypatch.setattr(server, "get_access_token", lambda: _fake_token(["read", "cop", "thief"]))
    server._assert_orchestrator()  # noqa: SLF001 - exercising the gate directly


def test_orchestrator_gate_rejects_single_role_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single-role token (only its own scope) cannot drive sync_state."""
    monkeypatch.setattr(server, "get_access_token", lambda: _fake_token(["read", "cop"]))
    with pytest.raises(ValueError, match="orchestrator token"):
        server._assert_orchestrator()  # noqa: SLF001


def test_orchestrator_gate_noop_without_http_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outside an HTTP context (in-memory) the gate is a no-op (token is None)."""
    monkeypatch.setattr(server, "get_access_token", lambda: None)
    server._assert_orchestrator()  # noqa: SLF001 - must not raise


def test_no_hardcoded_mcp_urls_in_src() -> None:
    """No inline ``http(s)://.../mcp`` literal lives in src/ — URLs come from config (E8)."""
    root = Path(pkg.__file__).parent
    pattern = re.compile(r"https?://[^\s\"']+/mcp")
    offenders: list[str] = []
    for src in root.rglob("*.py"):
        for i, line in enumerate(src.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{src.relative_to(root)}:{i}: {line.strip()}")
    assert not offenders, f"hardcoded MCP URL literals found: {offenders}"
