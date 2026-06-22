"""The :class:`Board` — the config-driven grid and its passability predicates (PRD §2).

A cell is ``(x, y)`` (column ``x``, row ``y``) with origin top-left. The board
never assumes ``width == height`` (non-square ladder rungs ``3x2``/``4x3`` are
supported). A barrier is impassable to *both* agents and behaves exactly like the
board edge. ``neighbors`` is 8-connected when ``allow_diagonal`` else 4-connected;
diagonals are king moves with **no** corner-cutting test (only the destination's
passability matters, per PRD §3).
"""

from __future__ import annotations

from cosmos77_ex06.game.state import Cell
from cosmos77_ex06.shared.config import Config

ORTHOGONAL: dict[str, Cell] = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
DIAGONAL: dict[str, Cell] = {"NE": (1, -1), "NW": (-1, -1), "SE": (1, 1), "SW": (-1, 1)}
STAY: dict[str, Cell] = {"STAY": (0, 0)}


class Board:
    """A ``width x height`` grid carrying the (cop-placed) barrier set."""

    def __init__(
        self,
        grid_size: list[int],
        allow_diagonal: bool,
        barriers: set[Cell] | None = None,
    ) -> None:
        self.width = int(grid_size[0])
        self.height = int(grid_size[1])
        self.allow_diagonal = bool(allow_diagonal)
        self.barriers: set[Cell] = set(barriers) if barriers else set()

    @classmethod
    def from_config(cls, config: Config) -> Board:
        """Build a fresh, barrier-free board from ``grid_size``/``allow_diagonal``."""
        return cls(
            grid_size=list(config.get("grid_size")),
            allow_diagonal=bool(config.get("allow_diagonal")),
        )

    @property
    def cells(self) -> list[Cell]:
        """Every in-bounds cell ``(x, y)`` in row-major order."""
        return [(x, y) for y in range(self.height) for x in range(self.width)]

    def directions(self) -> dict[str, Cell]:
        """The active named direction table (8-dir + STAY iff ``allow_diagonal``)."""
        table = {**ORTHOGONAL}
        if self.allow_diagonal:
            table.update(DIAGONAL)
        table.update(STAY)
        return table

    def in_bounds(self, pos: Cell) -> bool:
        """``True`` iff ``pos`` lies on the grid."""
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocked(self, pos: Cell) -> bool:
        """``True`` iff ``pos`` is a barrier cell."""
        return pos in self.barriers

    def is_passable(self, pos: Cell) -> bool:
        """``True`` iff ``pos`` is in-bounds and not a barrier."""
        return self.in_bounds(pos) and not self.is_blocked(pos)

    def neighbors(self, pos: Cell) -> list[Cell]:
        """The passable cells reachable in one step (excludes STAY)."""
        x, y = pos
        out: list[Cell] = []
        for name, (dx, dy) in self.directions().items():
            if name == "STAY":
                continue
            target = (x + dx, y + dy)
            if self.is_passable(target):
                out.append(target)
        return out

    def add_barrier(self, pos: Cell) -> None:
        """Mark ``pos`` as impassable for the remainder of the sub-game."""
        self.barriers.add(pos)
