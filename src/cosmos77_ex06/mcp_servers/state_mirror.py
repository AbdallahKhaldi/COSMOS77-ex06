"""Cloud state mirroring helpers — orchestrator-only ground-truth I/O (E6).

These back the ``sync_state`` / ``get_full_state`` tools that keep two SEPARATE-process
servers consistent in a cloud run. The orchestrator (authoritative owner) reads the
acting server's full board after a move and mirrors it to the other server, so the
engine never re-implements the game rules. These set / read internal TRUTH only;
``get_local_observation`` still redacts the opponent (E4 is untouched), and both tools
are gated to the orchestrator token at registration — the LLM never sees them.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.game.state import GameState


def overwrite_state(target: GameState, payload: dict[str, Any]) -> dict[str, Any]:
    """Overwrite ``target`` in place from a canonical state ``payload`` (E6).

    Writes every field of the orchestrator's canonical board onto the server's
    existing :class:`GameState` handle so callers keep their reference. Returns a tiny
    ack carrying the synced ``move_number``.
    """
    canonical = GameState.from_dict(payload)
    for field, value in vars(canonical).items():
        setattr(target, field, value)
    return {"ok": True, "move_number": int(target.move_number)}


def full_state(source: GameState) -> dict[str, Any]:
    """Return ``source``'s full ground truth as a canonical dict (orchestrator-only)."""
    return source.to_dict()
