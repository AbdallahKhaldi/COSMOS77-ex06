"""Command-line entry point for ``cosmos77-pursuit``.

A thin argparse dispatcher over the SDK. Each subcommand (run, report, bonus) is
wired to the SDK in its phase; until then it prints guidance. No business logic
lives here (CLAUDE.md rule 2 — all logic flows through the SDK).
"""

from __future__ import annotations

import argparse
import sys

from cosmos77_ex06.constants import CLI_COMMANDS


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with the run/report/bonus subcommands."""
    parser = argparse.ArgumentParser(
        prog="cosmos77-pursuit",
        description="Dual AI-agent Cops & Robbers over MCP (Orchestration of AI Agents 203.3763).",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    sub = parser.add_subparsers(dest="command", metavar="{" + ",".join(CLI_COMMANDS) + "}")

    run = sub.add_parser("run", help="run a Cops & Robbers game")
    run.add_argument("--local", action="store_true", help="target the local MCP servers")
    run.add_argument("--cloud", action="store_true", help="target the cloud MCP servers")
    run.add_argument("--gui", action="store_true", help="show the pygame viewer")
    run.add_argument("--games", type=int, default=None, help="override the sub-game count")
    run.add_argument("--grid", type=int, default=None, help="override the (square) grid size")
    run.add_argument(
        "--ladder",
        action="store_true",
        help="run the 2x2->3x3->4x4->5x5 sanity ladder, saving a transcript per size",
    )
    run.add_argument(
        "--log-file", default=None, help="tee the structured per-turn comms log to PATH (E10)"
    )

    rep = sub.add_parser("report", help="build / send the JSON report")
    rep.add_argument("--send", action="store_true", help="email the JSON report via Gmail")

    sub.add_parser("bonus", help="run the inter-group bonus series")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch. Returns a process exit code."""
    from cosmos77_ex06 import __version__

    args = build_parser().parse_args(argv)
    if args.version:
        print(f"cosmos77-pursuit {__version__}")
        return 0
    if args.command is None:
        build_parser().print_help()
        return 0
    return _dispatch(args)


def _dispatch(args: argparse.Namespace) -> int:
    """Route one subcommand to the SDK (stubs raise NotImplementedError per phase)."""
    from cosmos77_ex06.sdk.sdk import SDK

    sdk = SDK()
    if args.command == "run":
        _apply_run_overrides(sdk, args)
        _add_log_file(getattr(args, "log_file", None))
        if getattr(args, "ladder", False):
            for rung in sdk.run_sanity_ladder():
                print(
                    f"ladder {rung['grid']}: {rung['sub_games']} sub-games "
                    f"-> {rung['transcript_path']}"
                )
        else:
            out = sdk.run_full_game(cloud=getattr(args, "cloud", False), gui=args.gui)
            report = out["report"]
            print(f"totals: {report['totals']} ({len(report['sub_games'])} valid sub-games)")
    elif args.command == "report":
        sdk.report(send=args.send)
    elif args.command == "bonus":
        sdk.bonus()
    return 0


def _add_log_file(path: str | None) -> None:
    """Attach a file handler so the structured per-turn comms log is captured (E10)."""
    if not path:
        return
    import logging
    from pathlib import Path

    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
    logger = logging.getLogger("cosmos77_ex06")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _apply_run_overrides(sdk: object, args: argparse.Namespace) -> None:
    """Apply --games / --grid CLI overrides onto the SDK's loaded config in place."""
    data = sdk.config._data  # noqa: SLF001 - intentional CLI-time override of config
    if getattr(args, "games", None) is not None:
        data["num_games"] = int(args.games)
    if getattr(args, "grid", None) is not None:
        data["grid_size"] = [int(args.grid), int(args.grid)]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
