"""Tests for the serializable :class:`GameState` (PRD §8)."""

from __future__ import annotations

import json

from cosmos77_ex06.game.state import GameState


def _state() -> GameState:
    return GameState(
        grid_size=[5, 5],
        cop_pos=(4, 4),
        thief_pos=(0, 0),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
        barriers=[(3, 1), (1, 2)],
    )


def test_to_from_dict_round_trips() -> None:
    st = _state()
    st.add_message(0, "thief", "moving east")
    again = GameState.from_dict(st.to_dict())
    assert again.to_dict() == st.to_dict()
    assert again.cop_pos == (4, 4)
    assert again.barriers == [(1, 2), (3, 1)]


def test_barriers_serialize_sorted() -> None:
    st = _state()
    assert st.to_dict()["barriers"] == [[1, 2], [3, 1]]


def test_serialization_is_byte_stable() -> None:
    a = json.dumps(_state().to_dict(), sort_keys=True)
    b = json.dumps(_state().to_dict(), sort_keys=True)
    assert a == b


def test_add_message_keeps_order() -> None:
    st = _state()
    st.add_message(0, "thief", "first")
    st.add_message(1, "cop", "second")
    assert [m["text"] for m in st.messages] == ["first", "second"]


def test_default_status_and_scores() -> None:
    st = _state()
    assert st.status == "active"
    assert st.scores == {"cop": 0, "thief": 0}
    assert st.current_role == "thief"
