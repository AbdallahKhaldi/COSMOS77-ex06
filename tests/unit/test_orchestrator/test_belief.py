"""Partial-observability belief / deception-detection tests (E4/E11, PRD §6.2/§10)."""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.agents.base import make_agent
from cosmos77_ex06.shared.config import Config


def _obs(opponent_cell: tuple[int, int] | None) -> dict[str, Any]:
    """A partial view; the opponent appears as an occupant only when in-window."""
    cells: list[dict[str, Any]] = [{"x": 0, "y": 0, "blocked": False, "occupant": "cop"}]
    if opponent_cell is not None:
        cells.append(
            {"x": opponent_cell[0], "y": opponent_cell[1], "blocked": False, "occupant": "thief"}
        )
    return {"role": "cop", "self": {"x": 0, "y": 0}, "visible_cells": cells}


def test_belief_confirmed_when_opponent_in_view_discounts_bluff(orch_config: Config) -> None:
    """If the local view shows the opponent, a contradicting claim is DISCOUNTED."""
    agent = make_agent("cop", orch_config)
    est = agent.interpret(_obs((1, 1)), "I'm far away on the other side, don't bother.")
    assert est["seen"] is True
    assert est["opponent_cell"] == [1, 1]
    assert est["credibility"] == "confirmed"  # truth overrides the bluff


def test_belief_inferred_when_opponent_unseen(orch_config: Config) -> None:
    """With no local sighting, the belief rests on the opponent's words (inferred)."""
    agent = make_agent("cop", orch_config)
    est = agent.interpret(_obs(None), "Drifting along the western wall.")
    assert est["seen"] is False
    assert est["opponent_cell"] is None
    assert est["credibility"] == "inferred"
    assert est["heard"] == "Drifting along the western wall."


def test_belief_updates_when_opponent_message_changes(orch_config: Config) -> None:
    """The estimate changes when the incoming opponent message changes (belief update)."""
    agent = make_agent("cop", orch_config)
    first = agent.interpret(_obs(None), "Heading north.")
    second = agent.interpret(_obs(None), "Doubling back south now.")
    assert first["heard"] != second["heard"]
    assert first != second


def test_belief_none_when_silent(orch_config: Config) -> None:
    agent = make_agent("cop", orch_config)
    est = agent.interpret(_obs(None), None)
    assert est["credibility"] == "none"
    assert est["heard"] is None
