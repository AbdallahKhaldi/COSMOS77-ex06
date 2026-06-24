"""Shared fixtures for the web match-console tests — a FakeConfig + a built app."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cosmos77_ex06.web.app import build_app
from cosmos77_ex06.web.feed import MatchFeed

_DATA: dict[str, Any] = {
    "mcp": {
        "cop_url": "https://our-cop.example/mcp",
        "thief_url": "https://our-thief.example/mcp",
    },
    "web": {"public_url": "https://console.example"},
    "grid_size": [3, 3],
}


class FakeConfig:
    """Minimal Config double: dot-path ``get`` + ``env`` lookup + a tmp repo root."""

    def __init__(self, root: Path, env: dict[str, str] | None = None) -> None:
        self._data = dict(_DATA)
        self._env = env or {}
        self._root = root

    def get(self, key: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def env(self, key: str) -> str | None:
        return self._env.get(key)

    @property
    def config_dir(self) -> Path:
        return self._root / "config"


@pytest.fixture
def fake_config(tmp_path: Path) -> FakeConfig:
    (tmp_path / "config").mkdir()
    return FakeConfig(tmp_path, env={"WEB_PASSPHRASE": "open-sesame"})


@pytest.fixture
def app_and_feed(fake_config: FakeConfig) -> tuple[Any, MatchFeed, FakeConfig]:
    feed = MatchFeed()
    return build_app(fake_config, feed), feed, fake_config
