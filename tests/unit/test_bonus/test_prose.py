"""Prose translator — parse/format + the [row,col] <-> (x,y) axis map (verified vs NajAmjad)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.bonus import prose


@pytest.mark.parametrize(
    "text,intent,direction",
    [
        ("[INTENT: MOVE] The cop edges north-west.", "MOVE", "NW"),
        ("[INTENT: MOVE] The thief edges east.", "MOVE", "E"),
        ("[INTENT: MOVE] edges south.", "MOVE", "S"),
        ("[INTENT: BARRIER] The cop walls its cell and steps north-east.", "BARRIER", "NE"),
        ("[INTENT: HOLD] The thief holds position.", "HOLD", "STAY"),
    ],
)
def test_parse_move(text: str, intent: str, direction: str) -> None:
    assert prose.parse_move(text) == (intent, direction)


def test_parse_move_prefers_hyphenated_compass() -> None:
    """'north-east' must win over its substring 'north' (else every diagonal flips to a cardinal)."""
    assert prose.parse_move("[INTENT: MOVE] swings north-east now")[1] == "NE"


@pytest.mark.parametrize("bad", ["no signpost, just north", "[INTENT: MOVE] no compass here"])
def test_parse_move_raises_on_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        prose.parse_move(bad)


def test_format_move_roundtrips_through_parse() -> None:
    for d in ("N", "S", "E", "W", "NE", "NW", "SE", "SW"):
        assert prose.parse_move(prose.format_move("cop", "MOVE", d)) == ("MOVE", d)
    assert prose.parse_move(prose.format_move("thief", "MOVE", "STAY")) == ("HOLD", "STAY")


def test_coord_axis_map_matches_their_convention() -> None:
    """Their [row, col] == our (x=col, y=row); north=row-1, east=col+1 (verified live)."""
    assert prose.to_obs_cell((4, 0)) == [0, 4]  # our (x=4, y=0) -> their [row=0, col=4]
    assert prose.from_obs_cell([0, 4]) == (4, 0)
    assert prose.from_obs_cell(prose.to_obs_cell((2, 3))) == (2, 3)
