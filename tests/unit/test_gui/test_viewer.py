"""Viewer tests: headless no-op, off-screen PNG, theme, on_turn driver (G4/E10)."""

from __future__ import annotations

from pathlib import Path

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.gui import driver
from cosmos77_ex06.gui.theme import Theme
from cosmos77_ex06.gui.viewer import GameViewer, render_state_to_png
from cosmos77_ex06.shared.config import Config

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_render_state_to_png_writes_valid_png(
    tmp_path: Path, gui_config: Config, fixture_state: GameState
) -> None:
    out = render_state_to_png(fixture_state, tmp_path / "frame.png", gui_config)
    assert out.exists()
    assert out.read_bytes()[:8] == _PNG_MAGIC
    assert out.stat().st_size > 0


def test_render_state_to_png_creates_missing_dirs(
    tmp_path: Path, gui_config: Config, fixture_state: GameState
) -> None:
    out = render_state_to_png(fixture_state, tmp_path / "deep" / "nested" / "f.png", gui_config)
    assert out.exists() and out.read_bytes()[:8] == _PNG_MAGIC


def test_headless_viewer_is_noop(gui_config: Config, fixture_state: GameState) -> None:
    viewer = GameViewer(gui_config, force_headless=True)
    assert viewer.enabled is False
    # update / screenshot / close raise nothing and the game can keep running (E5).
    viewer.update(fixture_state)
    assert viewer.save_screenshot(fixture_state) is None
    viewer.close()


def test_theme_from_config_resolves_gui_block(gui_config: Config) -> None:
    theme = Theme.from_config(gui_config)
    assert theme.cell_size > 0 and theme.fps > 0
    assert len(theme.cop) == 3 and len(theme.thief) == 3
    assert theme.caption


def test_theme_defaults_when_gui_block_missing(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text('version: "1.00"\npaths: {assets: assets}\n', encoding="utf-8")
    theme = Theme.from_config(Config(cfg))
    assert theme.cell_size == 96  # default applied, no gui block present


def test_on_turn_driver_syncs_messages_and_updates_viewer(
    gui_config: Config, fixture_state: GameState
) -> None:
    seen: list[GameState] = []

    class _FakeViewer:
        def update(self, state: GameState) -> None:
            seen.append(state)

    class _FakeTranscript:
        def to_list(self) -> list[dict]:
            return [
                {"turn": 1, "role": "thief", "nl_message": "drifting west"},
                {"turn": 2, "role": "cop", "nl_message": "closing the gap"},
                {"turn": 3, "role": "thief", "nl_message": "sliding south now"},
            ]

    class _FakeEngine:
        transcript = _FakeTranscript()

    on_turn = driver.build_on_turn(_FakeEngine(), _FakeViewer())
    on_turn(fixture_state)
    assert seen and seen[0] is fixture_state
    texts = {m["role"]: m["text"] for m in fixture_state.messages}
    # Latest per role wins (thief's most recent line, not its first).
    assert texts["thief"] == "sliding south now"
    assert texts["cop"] == "closing the gap"
