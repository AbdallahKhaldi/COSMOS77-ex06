"""Sample-screenshot generator + log-emission wiring tests (E10/E11)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from cosmos77_ex06.sdk.sdk import SDK
from cosmos77_ex06.shared.config import Config

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "generate_sample_screenshots.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("gen_shots", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_frames_yields_three_named_states() -> None:
    module = _load_script()
    frames = module.build_frames(SDK())
    names = [name for name, _state in frames]
    assert names == ["gui_start", "gui_midgame", "gui_capture"]
    # The capture frame really has the cop on the thief's cell + injected messages.
    capture = dict(frames)["gui_capture"]
    assert tuple(capture.cop_pos) == tuple(capture.thief_pos)
    assert any("Capture" in m["text"] for m in capture.messages)


def test_generator_writes_three_valid_pngs(tmp_path: Path, gui_config: Config) -> None:
    from cosmos77_ex06.gui.viewer import render_state_to_png

    module = _load_script()
    for name, state in module.build_frames(SDK()):
        out = render_state_to_png(state, tmp_path / f"{name}.png", gui_config)
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(list(tmp_path.glob("*.png"))) == 3


@pytest.mark.live
def test_real_display_window_opens(gui_config: Config) -> None:  # pragma: no cover - live
    """Open a real pygame window (needs a screen; excluded from CI via 'live')."""
    from cosmos77_ex06.gui.viewer import GameViewer

    viewer = GameViewer(gui_config)
    viewer.close()
    assert True
