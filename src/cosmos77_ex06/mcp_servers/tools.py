"""Shared, role-aware MCP tool implementations over a :class:`GameState` handle.

No FastMCP and no LLM live here (E3) — these are plain methods so they unit-test
deterministically. The servers (``cop_server`` / ``thief_server``) wrap each method
in ``@mcp.tool``. Every action reuses the canonical ``game/`` engine — movement,
barrier, turn-order, and capture rules are never reimplemented (Rule 3). The
perception tools delegate redaction to :mod:`observation` so partial observability
(E4) is enforced server-side before anything crosses the wire.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.game import rules
from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import IllegalMoveError, apply_move, place_barrier
from cosmos77_ex06.game.state import Cell, GameState
from cosmos77_ex06.mcp_servers.observation import build_observation, confirm_position
from cosmos77_ex06.mcp_servers.state_mirror import full_state, overwrite_state
from cosmos77_ex06.shared.config import Config


class GameTools:
    """The tool surface bound to one role and one shared :class:`GameState`."""

    def __init__(self, state: GameState, config: Config, role: str) -> None:
        self.state = state
        self.config = config
        self.role = role
        self.vision_radius = int(config.get("vision_radius"))
        self.max_barriers = int(config.get("max_barriers"))
        self.turn_order = list(config.get("turn_order"))

    def _check_role(self, role: str) -> None:
        """Reject a call whose ``role`` does not match this server's identity."""
        if role != self.role:
            raise ValueError(f"{self.role} server cannot act for role {role!r}")

    def _board(self) -> Board:
        """A fresh :class:`Board` carrying the current barrier set."""
        return Board(self.state.grid_size, self.state.allow_diagonal, set(self.state.barriers))

    def send_message(self, role: str, content: str) -> dict[str, Any]:
        """Append a free natural-language message from ``role`` to the shared log (E4).

        ``content`` is opaque prose — intentions, claims, bluffs. The server is a
        transport + ledger only; it never parses or "understands" the message.

        NOTE (cloud-safety): this server-side log is LOCAL-ONLY — across separate
        processes the cop's stored message would not reach the thief's reader. The
        AUTHORITATIVE NL relay is the engine-held :class:`Transcript`
        (``last_from_opponent``), which is process-independent. This tool remains
        for native MCP tool-calling completeness and standalone server runs.
        """
        self._check_role(role)
        turn = int(self.state.move_number)
        self.state.add_message(turn, role, content)
        return {"ok": True, "turn": turn, "message_id": len(self.state.messages) - 1}

    def receive_messages(self, role: str, since: int = 0) -> dict[str, Any]:
        """Return the *opponent's* natural-language messages with id ``>= since`` (PRD §4.2).

        Prose the opponent chose to send, which may mislead. The caller's own prior
        messages are filtered out so a role never receives its own echo. LOCAL-ONLY
        (same caveat as :meth:`send_message`): the engine relays the opponent's last
        NL message via its own transcript, so the engine never depends on this tool.
        """
        self._check_role(role)
        msgs = [
            {"id": i, "turn": m["turn"], "from": m["role"], "content": m["text"]}
            for i, m in enumerate(self.state.messages)
            if i >= int(since) and m["role"] != role
        ]
        latest = msgs[-1]["id"] if msgs else int(since) - 1
        return {"messages": msgs, "latest_id": latest}

    def get_local_observation(self, role: str) -> dict[str, Any]:
        """Return only the partial, vision-windowed view ``role`` may see (E4)."""
        self._check_role(role)
        return build_observation(self.state, role, self.vision_radius, self.max_barriers)

    def verify_position(self, role: str, x: int, y: int) -> dict[str, Any]:
        """Confirm-only: is ``(x, y)`` the opponent's cell, if in-window? (PRD §4.4)."""
        self._check_role(role)
        return confirm_position(self.state, role, x, y, self.vision_radius)

    def apply_move(self, role: str, direction: str) -> dict[str, Any]:
        """Move ``role`` one step; enforce turn order + capture (PRD §4.5)."""
        self._check_role(role)
        if role != self.state.current_role:
            return {"ok": False, "new_self": None, "captured": False, "reason": "not your turn"}
        board = self._board()
        pos: Cell = tuple(self.state.cop_pos) if role == "cop" else tuple(self.state.thief_pos)
        try:
            new_pos = apply_move(pos, direction, board)
        except IllegalMoveError as exc:
            return {"ok": False, "new_self": None, "captured": False, "reason": str(exc)}
        setattr(self.state, "cop_pos" if role == "cop" else "thief_pos", new_pos)
        self.state.current_role = rules.next_role(role, self.turn_order)
        if role == self.turn_order[-1]:
            self.state.move_number += 1
        # Spec §4.3: capture is the COP landing on the thief — NOT the thief stepping
        # onto the cop. Gate on the actor so a thief move onto the cop never scores a win.
        captured = role == "cop" and rules.is_capture(self.state)
        return {
            "ok": True,
            "new_self": {"x": new_pos[0], "y": new_pos[1]},
            "captured": captured,
            "reason": None,
        }

    def sync_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Overwrite ground truth from the orchestrator's canonical board (cloud, E6)."""
        return overwrite_state(self.state, state)

    def get_full_state(self) -> dict[str, Any]:
        """Return the FULL ground truth for cloud mirroring (orchestrator-only, E6)."""
        return full_state(self.state)

    def place_barrier(self, role: str, x: int, y: int) -> dict[str, Any]:
        """Place a cop-only barrier impassable to both agents (PRD §4.6)."""
        self._check_role(role)
        board = self._board()
        try:
            used = place_barrier(
                role,
                (int(x), int(y)),
                board,
                self.state.barriers_used,
                self.max_barriers,
                tuple(self.state.cop_pos),
                tuple(self.state.thief_pos),
            )
        except IllegalMoveError as exc:
            remaining = self.max_barriers - self.state.barriers_used
            return {"ok": False, "cell": None, "barriers_remaining": remaining, "reason": str(exc)}
        self.state.barriers = sorted(board.barriers)
        self.state.barriers_used = used
        return {
            "ok": True,
            "cell": {"x": int(x), "y": int(y)},
            "barriers_remaining": self.max_barriers - used,
            "reason": None,
        }
