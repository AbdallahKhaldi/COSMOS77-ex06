"""Transcript recorder tests (PRD §9, E13 void notes)."""

from __future__ import annotations

from cosmos77_ex06.orchestrator.transcript import Transcript


def test_append_records_full_turn_entry() -> None:
    t = Transcript()
    entry = t.append(
        sub_game=1,
        turn=3,
        role="thief",
        nl_message="all quiet up north",
        tool="apply_move",
        args={"role": "thief", "direction": "SW"},
        board={"cop": [1, 4], "thief": [3, 0], "barriers": [], "move": 3},
        mcp_url="http://localhost:8002/mcp",
    )
    assert entry in t.to_list()
    assert t.messages() == ["all quiet up north"]


def test_note_void_is_recorded_separately() -> None:
    t = Transcript()
    t.note_void(2, "dropped MCP connection")
    assert t.voids == [{"sub_game": 2, "reason": "dropped MCP connection"}]
    assert t.to_list() == []  # a voided sub-game is not a scored turn record


def _turn(t: Transcript, sub_game: int, turn: int) -> None:
    t.append(
        sub_game=sub_game,
        turn=turn,
        role="thief",
        nl_message=f"turn {turn}",
        tool="apply_move",
        args={"direction": "STAY"},
        board={"cop": [1, 1], "thief": [0, 0], "barriers": [], "move": turn},
        mcp_url="http://localhost:8002/mcp",
    )


def test_truncate_drops_voided_attempt_turns_back_to_mark() -> None:
    """A voided attempt's partial turns are removed so the saved transcript is clean (E13)."""
    t = Transcript()
    _turn(t, 1, 1)  # a clean, valid sub-game's turn
    mark = t.mark()
    _turn(t, 2, 1)  # the voided attempt's turns...
    _turn(t, 2, 2)
    t.truncate(mark)  # ...are dropped on void
    t.note_void(2, "technical_loss")
    assert [e["sub_game"] for e in t.to_list()] == [1]
    assert t.voids == [{"sub_game": 2, "reason": "technical_loss"}]
