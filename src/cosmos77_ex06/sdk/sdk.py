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

    def new_game(self) -> Any:
        """Build a fresh :class:`GameState` from config (Phase 2)."""
        raise NotImplementedError("game state-machine lands in Phase 2")

    def run_local_game(self, *, gui: bool = False) -> dict[str, Any]:
        """Run a full game against the LOCAL MCP servers (Phase 4/6)."""
        raise NotImplementedError("the orchestrator loop lands in Phase 4")

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
