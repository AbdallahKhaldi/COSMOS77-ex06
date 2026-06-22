"""Append-only transcript recorder (graded evidence, PRD §9).

Each turn appends one entry — turn number, role, the free natural-language
message, the chosen tool + args, the resulting board snapshot, and the MCP server
URL the call hit. The transcript is the source for the GUI replay, the CLI logs
proving cloud-MCP comms, the README's example exchanges, and the report JSON.
"""

from __future__ import annotations

from typing import Any


class Transcript:
    """A growing list of turn records plus voided-sub-game notes (E13)."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.voids: list[dict[str, Any]] = []

    def append(
        self,
        *,
        sub_game: int,
        turn: int,
        role: str,
        nl_message: str,
        tool: str | None,
        args: dict[str, Any],
        board: dict[str, Any],
        mcp_url: str,
        coord_flagged: bool = False,
        estimate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record one turn and return the stored entry.

        ``coord_flagged`` is the E4 guard verdict for ``nl_message`` (True if the
        outgoing message leaked a coordinate-shaped token, PRD §7.5/§10).
        ``estimate`` is the agent's private partial-observability belief about the
        opponent (E4/E11 inference evidence, PRD §6.2).
        """
        entry = {
            "sub_game": sub_game,
            "turn": turn,
            "role": role,
            "nl_message": nl_message,
            "tool": tool,
            "args": dict(args),
            "board": board,
            "mcp_url": mcp_url,
            "coord_flagged": bool(coord_flagged),
            "estimate": dict(estimate) if estimate else {},
        }
        self.entries.append(entry)
        return entry

    def note_void(self, sub_game: int, reason: str) -> None:
        """Record a Technical-Loss void (the sub-game is not scored; E13)."""
        self.voids.append({"sub_game": sub_game, "reason": reason})

    def messages(self) -> list[str]:
        """All natural-language messages exchanged, in order (E4 evidence)."""
        return [e["nl_message"] for e in self.entries]

    def to_list(self) -> list[dict[str, Any]]:
        """Return a shallow copy of all turn records."""
        return list(self.entries)

    def last_from_opponent(self, role: str) -> str | None:
        """The most recent NL message NOT authored by ``role`` (E4 relay)."""
        for entry in reversed(self.entries):
            if entry["role"] != role:
                return entry["nl_message"]
        return None
