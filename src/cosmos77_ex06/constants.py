"""Project-wide structural constants (not tunable config — see CLAUDE.md rule 4).

Fixed enumerations the game, agents, and orchestrator share. Tunable values
(grid size, moves, games, barriers, scoring, ports, MCP URLs, model) live in
``config/config.yaml`` and ``.env`` and are read via the Config loader.
"""

from __future__ import annotations

#: Default text encoding for all file I/O across the project.
DEFAULT_ENCODING: str = "utf-8"

#: The importable package name (mirrors pyproject ``name``, underscored).
PACKAGE_NAME: str = "cosmos77_ex06"

#: The version string — kept in lockstep with pyproject and every config file.
PROJECT_VERSION: str = "1.00"

#: The two agent roles in the pursuit.
ROLES: tuple[str, ...] = ("thief", "cop")

#: The ``cosmos77-pursuit`` CLI subcommands (wired to the SDK per phase).
CLI_COMMANDS: tuple[str, ...] = (
    "run",
    "report",
    "bonus",
)
