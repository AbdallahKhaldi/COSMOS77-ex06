"""Fixtures for the GUI suite — dummy SDL driver, no screen, deterministic (rule 17).

All GUI tests run headless: the dummy SDL video/audio drivers let pygame init and
draw against an off-screen surface, so nothing here needs a physical display
(PRD_gui §4/§8). A small fixture :class:`GameState` and a :class:`Config` (loaded
from the real repo config so the ``gui:`` block resolves) drive the assertions.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from cosmos77_ex06.game.state import GameState  # noqa: E402
from cosmos77_ex06.shared.config import Config  # noqa: E402

_REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture
def gui_config() -> Config:
    """The real repo Config (its ``gui:`` block exercises the theme resolver)."""
    return Config(_REPO_CONFIG)


@pytest.fixture
def fixture_state() -> GameState:
    """A 5x5 state with two barriers and both agents' latest NL messages."""
    state = GameState(
        grid_size=[5, 5],
        cop_pos=(4, 4),
        thief_pos=(0, 0),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
        barriers=[(2, 2), (3, 2)],
        barriers_used=2,
        move_number=7,
        current_role="thief",
    )
    state.add_message(6, "thief", "Hugging the western wall, staying clear of open ground.")
    state.add_message(7, "cop", "I think you're north-west; cutting off the top-left.")
    return state
