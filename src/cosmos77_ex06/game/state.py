"""The single serializable :class:`GameState` (PRD §8).

This is the one object the GUI renders, the report serializes, and the MCP tools
project a *partial* view of. Serialization is deterministic: ``barriers`` is a
sorted list and ``messages`` keeps insertion order, so the same logical state
always produces byte-identical JSON (reused by the canonical serializer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Cell = tuple[int, int]


@dataclass
class SubGameResult:
    """The outcome of one sub-game (PRD §6.2): winner, scores, log, TL flag."""

    winner: str
    scores: dict[str, int]
    move_count: int
    state: GameState
    log: list[dict[str, Any]] = field(default_factory=list)
    technical_loss: bool = False


@dataclass
class GameState:
    """Ground-truth board state for one sub-game (PRD §8)."""

    grid_size: list[int]
    cop_pos: Cell
    thief_pos: Cell
    max_moves: int
    allow_diagonal: bool
    turn_order: list[str]
    barriers: list[Cell] = field(default_factory=list)
    barriers_used: int = 0
    move_number: int = 0
    current_role: str = "thief"
    messages: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"
    scores: dict[str, int] = field(default_factory=lambda: {"cop": 0, "thief": 0})

    def add_message(self, turn: int, role: str, text: str) -> None:
        """Append a free natural-language transcript entry."""
        self.messages.append({"turn": turn, "role": role, "text": text})

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic, JSON-serializable mapping (sorted barriers)."""
        return {
            "grid_size": list(self.grid_size),
            "cop_pos": list(self.cop_pos),
            "thief_pos": list(self.thief_pos),
            "max_moves": self.max_moves,
            "allow_diagonal": self.allow_diagonal,
            "turn_order": list(self.turn_order),
            "barriers": [list(b) for b in sorted(self.barriers)],
            "barriers_used": self.barriers_used,
            "move_number": self.move_number,
            "current_role": self.current_role,
            "messages": [dict(m) for m in self.messages],
            "status": self.status,
            "scores": dict(self.scores),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        """Round-trip a mapping produced by :meth:`to_dict` back into a state."""
        return cls(
            grid_size=list(data["grid_size"]),
            cop_pos=tuple(data["cop_pos"]),
            thief_pos=tuple(data["thief_pos"]),
            max_moves=int(data["max_moves"]),
            allow_diagonal=bool(data["allow_diagonal"]),
            turn_order=list(data["turn_order"]),
            barriers=[tuple(b) for b in data.get("barriers", [])],
            barriers_used=int(data.get("barriers_used", 0)),
            move_number=int(data.get("move_number", 0)),
            current_role=str(data.get("current_role", "thief")),
            messages=[dict(m) for m in data.get("messages", [])],
            status=str(data.get("status", "active")),
            scores=dict(data.get("scores", {"cop": 0, "thief": 0})),
        )
