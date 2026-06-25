"""Translate between NajAmjad's prose move contract and our vocabulary (bonus interop, E12).

Their ``request_move`` returns ``"[INTENT: MOVE|BARRIER|HOLD] <prose with one compass word>"``.
Their board is ``[row, col]`` (north = row-1, east = col+1); ours is ``(x, y)`` with ``x=col,
y=row`` and names N/S/E/W/NE/NW/SE/SW/STAY. This is the single tested seam that keeps the two
conventions in lockstep so a move can never silently flip an axis (a flipped axis => a wrong
game => a hash mismatch => 0/0). Verified live against their servers 2025.
"""

from __future__ import annotations

import re

#: their compass word -> our direction name (hyphenated forms MUST be matched first)
COMPASS_TO_DIR = {
    "north-east": "NE",
    "north-west": "NW",
    "south-east": "SE",
    "south-west": "SW",
    "north": "N",
    "south": "S",
    "east": "E",
    "west": "W",
}
DIR_TO_COMPASS = {v: k for k, v in COMPASS_TO_DIR.items()}
_INTENT_RE = re.compile(r"\[INTENT:\s*(MOVE|BARRIER|HOLD)\s*\]", re.IGNORECASE)


def to_obs_cell(pos: tuple[int, int]) -> list[int]:
    """Our ``(x, y)`` -> their observation cell ``[row, col]`` (their row=our y, col=our x)."""
    return [int(pos[1]), int(pos[0])]


def from_obs_cell(cell: list[int]) -> tuple[int, int]:
    """Their ``[row, col]`` -> our ``(x, y)`` = ``(col, row)``."""
    return (int(cell[1]), int(cell[0]))


def parse_move(prose: str) -> tuple[str, str]:
    """Parse ``"[INTENT: ...] ... <compass> ..."`` into ``(intent, our_direction)``.

    ``HOLD`` -> ``STAY``. A ``BARRIER`` reply keeps its compass as the step direction.
    Raises :class:`ValueError` on a missing signpost or compass word so the caller can
    void + re-run that sub-game rather than apply a garbage move (E13).
    """
    match = _INTENT_RE.search(prose or "")
    if not match:
        raise ValueError(f"no [INTENT: ...] signpost in: {prose!r}")
    intent = match.group(1).upper()
    if intent == "HOLD":
        return intent, "STAY"
    low = (prose or "").lower()
    for word in sorted(COMPASS_TO_DIR, key=len, reverse=True):
        if word in low:
            return intent, COMPASS_TO_DIR[word]
    raise ValueError(f"no compass word in: {prose!r}")


def format_move(role: str, intent: str, direction: str) -> str:
    """Build a reply in their contract: ``"[INTENT: ...] The <role> ... <compass>."``."""
    if direction == "STAY" or intent == "HOLD":
        return f"[INTENT: HOLD] The {role} holds position."
    verb = "walls its cell and steps" if intent == "BARRIER" else "edges"
    return f"[INTENT: {intent}] The {role} {verb} {DIR_TO_COMPASS[direction]}."
