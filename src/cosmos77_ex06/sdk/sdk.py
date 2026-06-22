"""The single business-logic entry point (CLAUDE.md rule 2).

The CLI, GUI, and orchestrator all go through ``class SDK`` — one audited surface,
one method per pipeline stage, over ONE Gatekeeper ledger in ``results/``.
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

    @property
    def reports_dir(self) -> Path:
        """The repo-rooted ``reports/`` output directory."""
        return self.repo_root / self.config.paths().get("reports", "reports")

    def new_game(self, *, cop_start: Any = None, thief_start: Any = None) -> Any:
        """Build a fresh :class:`GameState` from config (opposite corners; Phase 2)."""
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
        """Apply one ``("move", direction)`` / ``("barrier", cell)`` for ``role``.

        An illegal action raises :class:`~cosmos77_ex06.game.moves.IllegalMoveError`.
        """
        from cosmos77_ex06.game import rules
        from cosmos77_ex06.game.board import Board
        from cosmos77_ex06.game.moves import apply_move, place_barrier

        kind, payload = action
        board = Board(state.grid_size, state.allow_diagonal, set(state.barriers))
        pos = state.cop_pos if role == "cop" else state.thief_pos
        if kind == "barrier":
            cap = int(self.config.get("max_barriers"))
            args = (board, state.barriers_used, cap, state.cop_pos, state.thief_pos)
            state.barriers_used = place_barrier(role, tuple(payload), *args)
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
        """Run a full game vs the LOCAL MCP servers (E3/E4/E5); ``client_factory`` mocks genai."""
        import asyncio

        from cosmos77_ex06.orchestrator.local import run_local_game

        return asyncio.run(run_local_game(self.config, self.gatekeeper, client_factory, gui=gui))

    def run_full_game(
        self, *, cloud: bool = False, gui: bool = False, sender: Any = None, **kw: Any
    ) -> dict[str, Any]:
        """Run an autonomous full game (6 valid sub-games), validate + save the report.

        Re-runs Technical-Losses to ``num_games`` valid sub-games (E5, E13); ``cloud=True``
        targets the config HTTPS MCP URLs (E6); ``report.auto_send`` true makes the COP email
        the JSON at game end (E7). ``client_factory``/``mcp_client_factory``/``sender`` mock in tests.
        """
        import asyncio

        from cosmos77_ex06.orchestrator.runner import run_full_game
        from cosmos77_ex06.report import output
        from cosmos77_ex06.report.schema import validate_internal_game

        client_factory = kw.get("client_factory")
        kwargs = {"cloud": cloud, "gui": gui, "mcp_client_factory": kw.get("mcp_client_factory")}
        outcome = asyncio.run(run_full_game(self.config, self.gatekeeper, client_factory, **kwargs))
        report = outcome["report"]
        validate_internal_game(report)
        path = output.save_report(self.reports_dir, report)
        self.gatekeeper.record("full_game", {"totals": report["totals"], "report_path": str(path)})
        if bool(self.config.get("report.auto_send", default=False)):
            from cosmos77_ex06.report import dispatch

            dispatch.auto_send(self.config, self.gatekeeper, report, sender)
        return {"report": report, "transcript": outcome["transcript"]}

    def run_sanity_ladder(self, client_factory: Any = None) -> list[dict[str, Any]]:
        """Run the 2x2->5x5 sanity ladder, saving a transcript per size (spec §4.5)."""
        from cosmos77_ex06.report import output

        return output.run_sanity_ladder(
            self.config, self.reports_dir, self.run_full_game, client_factory
        )

    def report(self, *, send: bool = False, sender: Any = None) -> dict[str, Any]:
        """Load + validate the latest report JSON; optionally Gmail-send it (E7, ``report --send``)."""
        from cosmos77_ex06.report import dispatch

        return dispatch.send_latest(
            self.config, self.gatekeeper, self.reports_dir, send=send, sender=sender
        )

    def bonus(self, *, client_factory: Any = None, save: bool = True) -> dict[str, Any]:
        """Run the inter-group bonus role-swap series + byte-stable bonus_game JSON (E12)."""
        from cosmos77_ex06.bonus.run import run_bonus

        return run_bonus(
            self.config, self.gatekeeper, self.reports_dir, client_factory=client_factory, save=save
        )

    def ledger(self) -> dict[str, Any]:
        """Return the aggregated result ledger (all results/*.json)."""
        return self.gatekeeper.ledger()
