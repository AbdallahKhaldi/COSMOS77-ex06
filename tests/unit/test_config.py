"""Tests for the YAML config loader (CLAUDE.md rule 4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cosmos77_ex06.shared.config import Config


def test_loads_version_and_config_dir(config: Config, config_dir: Path) -> None:
    assert config.version == "1.00"
    assert config.config_dir == config_dir


def test_dot_path_get_nested(config: Config) -> None:
    assert config.get("mcp.cop_url") == "http://localhost:8001/mcp"
    assert config.get("scoring.cop_win") == 20
    assert config.get("grid_size") == [5, 5]


def test_get_missing_raises_without_default(config: Config) -> None:
    with pytest.raises(KeyError):
        config.get("mcp.nonexistent")


def test_get_missing_returns_default(config: Config) -> None:
    assert config.get("mcp.nope", default="fallback") == "fallback"


def test_paths_section(config: Config) -> None:
    assert config.paths() == {"results": "results", "reports": "reports", "assets": "assets"}


def test_env_reads_environment(config: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "sentinel-value")
    assert config.env("GEMINI_API_KEY") == "sentinel-value"
    assert config.env("DEFINITELY_UNSET", default="d") == "d"


def test_version_mismatch_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text(yaml.safe_dump({"version": "9.99"}), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match project version"):
        Config(cfg)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Config(tmp_path / "config")


def test_non_mapping_top_level_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        Config(cfg)


def test_from_path_classmethod(config_dir: Path) -> None:
    loaded = Config.from_path(config_dir)
    assert loaded.version == "1.00"


def test_repr_includes_version(config: Config) -> None:
    assert "1.00" in repr(config)
