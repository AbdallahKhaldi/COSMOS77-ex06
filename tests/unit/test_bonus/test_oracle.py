"""Our request_move oracle + server — deterministic move from an observation, token-gated."""

from __future__ import annotations

from typing import Any

import pytest

from cosmos77_ex06.bonus import oracle, prose, request_server
from cosmos77_ex06.shared.config import Config


def _obs(role: str, cop: tuple, thief: tuple) -> dict[str, Any]:
    return {
        "role": role,
        "grid": [5, 5],
        "cop": prose.to_obs_cell(cop),
        "thief": prose.to_obs_cell(thief),
        "barriers": [],
        "barriers_left": 5,
        "variant": 0,
        "turn": 0,
    }


def test_oracle_answers_both_roles_in_contract_form() -> None:
    cfg = Config()
    intent, _ = prose.parse_move(oracle.decide(_obs("cop", (4, 4), (0, 0)), cfg))
    assert intent == "MOVE"
    intent2, _ = prose.parse_move(oracle.decide(_obs("thief", (1, 1), (3, 3)), cfg))
    assert intent2 == "MOVE"


def test_oracle_is_deterministic() -> None:
    cfg = Config()
    o = _obs("cop", (4, 4), (1, 2))
    assert oracle.decide(o, cfg) == oracle.decide(o, cfg)


async def test_request_move_server_gates_on_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OUR_BONUS_TOKEN", "secret-cop")
    from fastmcp import Client

    srv = request_server.build("cop")
    async with Client(srv) as client:
        bad = await client.call_tool(
            "request_move", {"observation": _obs("cop", (4, 4), (0, 0)), "auth_token": "wrong"}
        )
        good = await client.call_tool(
            "request_move", {"observation": _obs("cop", (4, 4), (0, 0)), "auth_token": "secret-cop"}
        )

    def _text(r: Any) -> str:
        return r.data if getattr(r, "data", None) else r.content[0].text

    assert "unauthorized" in _text(bad).lower()
    assert _text(good).startswith("[INTENT:")
