"""The single business-logic entry point (CLAUDE.md rule 2).

The CLI, the GUI, and the orchestrator all go through ``class SDK`` — one audited
surface, one method per pipeline stage. Each stage lands in its phase (a
``NotImplementedError`` until then). The Gatekeeper (LLM meter + result ledger) is
created once over ``results/`` so every transcript and report rests on ONE ledger.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


class SDK:
    """All business logic for the Cops & Robbers MCP-orchestration pipeline."""

    def __init__(
        self,
        config: Config | None = None,
        gatekeeper: Gatekeeper | None = None,
        results_dir: Path | str | None = None,
    ) -> None:
        self.config = config or Config()
        if results_dir is not None:
            self.results_dir = Path(results_dir)
        else:
            self.results_dir = self.repo_root / self.config.paths().get("results", "results")
        self.gatekeeper = gatekeeper or Gatekeeper(self.results_dir)

    @property
    def repo_root(self) -> Path:
        """The repository root (the parent of the ``config/`` directory)."""
        return self.config.config_dir.parent

    def new_game(self, *, cop_start: Any = None, thief_start: Any = None) -> Any:
        """Build a fresh :class:`GameState` from config (Phase 2).

        Start positions default to opposite corners of the grid. The fresh state
        is recorded through the gatekeeper ledger so every transcript rests on one
        ledger.
        """
        from cosmos77_ex06.game.state import GameState

        grid = list(self.config.get("grid_size"))
        cop = tuple(cop_start) if cop_start is not None else (grid[0] - 1, grid[1] - 1)
        thief = tuple(thief_start) if thief_start is not None else (0, 0)
        turn_order = list(self.config.get("turn_order"))
        state = GameState(
            grid_size=grid,
            cop_pos=cop,
            thief_pos=thief,
            max_moves=int(self.config.get("max_moves")),
            allow_diagonal=bool(self.config.get("allow_diagonal")),
            turn_order=turn_order,
            current_role=turn_order[0],
        )
        self.gatekeeper.record("new_game", {"state": state.to_dict()})
        return state

    def step(self, state: Any, role: str, action: Any) -> Any:
        """Apply one ``(action, payload)`` for ``role`` and return the new state.

        ``action`` is ``("move", direction)`` or ``("barrier", cell)``. Movement
        and barrier rules are enforced; an illegal action raises
        :class:`~cosmos77_ex06.game.moves.IllegalMoveError`.
        """
        from cosmos77_ex06.game import rules
        from cosmos77_ex06.game.board import Board
        from cosmos77_ex06.game.moves import apply_move, place_barrier

        kind, payload = action
        board = Board(state.grid_size, state.allow_diagonal, set(state.barriers))
        pos = state.cop_pos if role == "cop" else state.thief_pos
        if kind == "barrier":
            state.barriers_used = place_barrier(
                role,
                tuple(payload),
                board,
                state.barriers_used,
                int(self.config.get("max_barriers")),
                state.cop_pos,
                state.thief_pos,
            )
            state.barriers = sorted(board.barriers)
        else:
            new_pos = apply_move(pos, payload, board)
            if role == "cop":
                state.cop_pos = new_pos
            else:
                state.thief_pos = new_pos
        state.current_role = rules.next_role(role, list(state.turn_order))
        return state

    def run_local_game(self, *, gui: bool = False, client_factory: Any = None) -> dict[str, Any]:
        """Run a full game against the LOCAL MCP servers and return transcript + totals.

        Drives the orchestrator (:class:`GameEngine`) against in-memory FastMCP
        clients bound to the cop + thief servers (E3/E4/E5). ``client_factory``
        injects a mock google-genai client for tests; omit it for a live run.
        """
        import asyncio

        from cosmos77_ex06.orchestrator.local import run_local_game

        return asyncio.run(run_local_game(self.config, self.gatekeeper, client_factory))

    def run_full_game(self, *, cloud: bool = False) -> dict[str, Any]:
        """Run an autonomous game (6 valid sub-games) and assemble the report (Phase 7/8)."""
        raise NotImplementedError("the autonomous runner lands in Phase 7")

    def report(self, *, send: bool = False) -> Any:
        """Build (and optionally Gmail-send) the internal-game JSON report (Phase 9)."""
        raise NotImplementedError("the report builder + Gmail sender land in Phase 9")

    def bonus(self) -> Any:
        """Run the inter-group bonus series + build the bonus_game JSON (Phase 11)."""
        raise NotImplementedError("the inter-group bonus harness lands in Phase 11")

    def ledger(self) -> dict[str, Any]:
        """Return the aggregated result ledger (all results/*.json)."""
        return self.gatekeeper.ledger()
