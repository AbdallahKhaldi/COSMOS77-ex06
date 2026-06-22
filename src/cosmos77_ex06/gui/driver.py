"""Bridge the live :class:`GameEngine` to the pygame :class:`GameViewer` (E10).

The engine relays opponent messages through its in-memory :class:`Transcript`
(not ``state.messages`` — that keeps the relay process-independent, E4). For the
viewer we need the latest free NL line per role visible on the board, so the
``on_turn`` callback this module builds copies the most-recent transcript message
per role into a transient ``messages`` view on the SAME state object purely for
rendering — it never changes positions, barriers, scores, or the relay path, so
``gui=False`` behaviour is byte-identical. Headless safety lives in the viewer
itself: when no display is available ``update`` is a no-op.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def build_on_turn(engine: Any, viewer: Any) -> Callable[[Any], None]:
    """Return an ``on_turn(state)`` callback that refreshes the viewer each turn."""

    def _on_turn(state: Any) -> None:
        state.messages = _latest_messages(engine.transcript)
        viewer.update(state)

    return _on_turn


def _latest_messages(transcript: Any) -> list[dict[str, Any]]:
    """Build a ``[{turn, role, text}]`` view: the latest NL line per role."""
    latest: dict[str, dict[str, Any]] = {}
    for entry in transcript.to_list():
        latest[entry["role"]] = {
            "turn": entry["turn"],
            "role": entry["role"],
            "text": entry["nl_message"],
        }
    return list(latest.values())
