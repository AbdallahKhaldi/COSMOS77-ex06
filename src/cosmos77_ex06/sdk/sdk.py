"""The single business-logic entry point (CLAUDE.md rule 2).

The CLI, GUI, and orchestrator all go through ``class SDK`` — one audited surface,
one method per pipeline stage, over ONE Gatekeeper ledger in ``results/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cosmos77_ex06.sdk.game_ops import GameOpsMixin
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


class SDK(GameOpsMixin):
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

    def run_local_game(self, *, gui: bool = False, client_factory: Any = None) -> dict[str, Any]:
        """Run a full game vs the LOCAL MCP servers (E3/E4/E5); ``client_factory`` mocks genai."""
        import asyncio

        from cosmos77_ex06.orchestrator.local import run_local_game

        return asyncio.run(run_local_game(self.config, self.gatekeeper, client_factory, gui=gui))

    def run_full_game(
        self, *, cloud: bool = False, gui: bool = False, sender: Any = None, **kw: Any
    ) -> dict[str, Any]:
        """Run an autonomous full game (6 valid sub-games), validate + save it; ``cloud=True`` uses HTTPS URLs (E5/E6/E13)."""
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

    def _send(self, which: str, **kw: Any) -> dict[str, Any]:
        """Shared report/bonus Gmail-send plumbing; ``which`` selects the dispatch function."""
        from cosmos77_ex06.report import dispatch

        return getattr(dispatch, which)(self.config, self.gatekeeper, self.reports_dir, **kw)

    def report(
        self, *, send: bool = False, sender: Any = None, to: str | None = None, final: bool = False
    ) -> dict[str, Any]:
        """Load+validate the latest report; Gmail-send it; ``final`` required for the professor (E7)."""
        return self._send("send_latest", send=send, sender=sender, to=to, final=final)

    def bonus(self, *, client_factory: Any = None, save: bool = True) -> dict[str, Any]:
        """Run the inter-group bonus role-swap series + byte-stable bonus_game JSON (E12)."""
        from cosmos77_ex06.bonus.run import run_bonus

        return run_bonus(
            self.config, self.gatekeeper, self.reports_dir, client_factory=client_factory, save=save
        )

    def send_bonus(
        self, *, send: bool = True, sender: Any = None, to: str | None = None, final: bool = False
    ) -> dict[str, Any]:
        """Validate + Gmail-send the existing bonus_game.json; ``final`` required for the professor (E12)."""
        return self._send("send_bonus", send=send, sender=sender, to=to, final=final)

    def ledger(self) -> dict[str, Any]:
        """Return the aggregated result ledger (all results/*.json)."""
        return self.gatekeeper.ledger()
