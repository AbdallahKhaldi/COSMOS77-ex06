"""YAML + .env config loader for COSMOS77-ex06 (CLAUDE.md rule 4 / spec §10).

Every module reads its tunables through :class:`Config`, so the grid size, moves,
games, barriers, scoring, ports, MCP URLs, and the model are never hardcoded.
``config/config.yaml`` is version-checked at load; ``.env`` supplies the secrets
(``GEMINI_API_KEY``, the MCP tokens). Access is by dot-path (``mcp.cop_url``).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from cosmos77_ex06.shared.version import validate_config_version

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
_SENTINEL: Any = object()


class Config:
    """Loads ``config.yaml`` and exposes dot-path access + ``.env`` secrets."""

    def __init__(self, config_dir: Path | str | None = None) -> None:
        self._config_dir = Path(config_dir) if config_dir is not None else _DEFAULT_CONFIG_DIR
        self._data = self._load_yaml("config.yaml")
        validate_config_version(str(self._data.get("version", "")))
        load_dotenv(self._config_dir.parent / ".env", override=False)

    @classmethod
    def from_path(cls, path: Path | str) -> Config:
        """Construct from an explicit ``config/`` directory."""
        return cls(path)

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self._config_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing required config file: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a YAML mapping at the top level")
        return data

    def get(self, dot_path: str, default: Any = _SENTINEL) -> Any:
        """Return the value at ``dot_path`` (e.g. ``mcp.cop_url`` or ``scoring.cop_win``)."""
        node: Any = self._data
        for part in dot_path.split("."):
            if isinstance(node, Mapping) and part in node:
                node = node[part]
            else:
                if default is _SENTINEL:
                    raise KeyError(dot_path)
                return default
        return node

    def env(self, key: str, default: str | None = None) -> str | None:
        """Read an environment variable (after ``.env`` has been loaded)."""
        return os.environ.get(key, default)

    def paths(self) -> dict[str, str]:
        """The ``paths`` section (results, reports, assets)."""
        return dict(self.get("paths", default={}))

    @property
    def version(self) -> str:
        """The ``config.yaml`` version string (e.g. ``"1.00"``)."""
        return str(self._data.get("version", ""))

    @property
    def config_dir(self) -> Path:
        """The directory the loader was pointed at."""
        return self._config_dir

    def __repr__(self) -> str:
        return f"Config(version={self.version!r}, dir={self._config_dir})"
