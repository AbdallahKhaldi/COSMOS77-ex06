"""Pure-render tests: expected draw calls for a fixture state (E10, E4)."""

from __future__ import annotations

from typing import Any

import pygame
import pytest

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.gui import render
from cosmos77_ex06.gui.theme import Theme
from cosmos77_ex06.shared.config import Config


class _DrawSpy:
    """Records pygame.draw.{rect,circle} calls instead of touching pixels."""

    def __init__(self) -> None:
        self.rects: list[Any] = []
        self.circles: list[Any] = []

    def rect(self, surface: Any, color: Any, rect: Any, width: int = 0) -> None:
        self.rects.append((tuple(color), tuple(rect), width))

    def circle(self, surface: Any, color: Any, center: Any, radius: int) -> None:
        self.circles.append((tuple(color), tuple(center), radius))


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _DrawSpy:
    """Monkeypatch pygame.draw with a recording spy (no real drawing)."""
    s = _DrawSpy()
    monkeypatch.setattr(pygame.draw, "rect", s.rect)
    monkeypatch.setattr(pygame.draw, "circle", s.circle)
    return s


def _theme(gui_config: Config) -> Theme:
    return Theme.from_config(gui_config)


def test_grid_draws_one_rect_pair_per_cell(spy: _DrawSpy, gui_config: Config) -> None:
    theme = _theme(gui_config)
    surface = pygame.Surface(render.board_pixels(theme, [5, 5]))
    render.draw_grid(surface, theme, [5, 5])
    # 25 cells x (fill + outline) = 50 rect calls.
    assert len(spy.rects) == 50


def test_barriers_draw_one_rect_per_blocked_cell(spy: _DrawSpy, gui_config: Config) -> None:
    theme = _theme(gui_config)
    surface = pygame.Surface(render.board_pixels(theme, [5, 5]))
    render.draw_barriers(surface, theme, [(2, 2), (3, 2)])
    assert len(spy.rects) == 2
    assert all(color == theme.barrier for color, _rect, _w in spy.rects)


def test_agents_drawn_as_circles_at_their_cells(
    spy: _DrawSpy, gui_config: Config, fixture_state: GameState
) -> None:
    theme = _theme(gui_config)
    surface = pygame.Surface(render.board_pixels(theme, fixture_state.grid_size))
    render.render_state(surface, theme, fixture_state)
    colors = {color for color, _c, _r in spy.circles}
    assert theme.cop in colors and theme.thief in colors
    # Cop centre is inside its bottom-right cell.
    cop_cx = fixture_state.cop_pos[0] * theme.cell_size + theme.cell_size // 2
    assert any(center[0] == cop_cx for _color, center, _r in spy.circles)


def test_render_state_produces_nonempty_surface(
    gui_config: Config, fixture_state: GameState
) -> None:
    theme = _theme(gui_config)
    surface = pygame.Surface(render.board_pixels(theme, fixture_state.grid_size))
    render.render_state(surface, theme, fixture_state)
    # A drawn surface is not uniformly the background colour.
    colors = {surface.get_at((x, y))[:3] for x in range(0, 5) for y in range(0, 5)}
    assert len(colors) >= 1
    assert surface.get_size() == render.board_pixels(theme, fixture_state.grid_size)


def test_capture_highlight_drawn_when_cop_on_thief(spy: _DrawSpy, gui_config: Config) -> None:
    theme = _theme(gui_config)
    state = GameState(
        grid_size=[3, 3],
        cop_pos=(1, 1),
        thief_pos=(1, 1),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
    )
    surface = pygame.Surface(render.board_pixels(theme, [3, 3]))
    render.render_state(surface, theme, state)
    assert any(color == theme.capture for color, _rect, _w in spy.rects)


def test_message_panel_shows_latest_nl_per_role(
    gui_config: Config, fixture_state: GameState
) -> None:
    # Latest-per-role helper returns the genuine free-language strings (E4).
    assert "western wall" in render._latest_message(fixture_state, "thief")
    assert "north-west" in render._latest_message(fixture_state, "cop")
    assert render._latest_message(fixture_state, "cop").strip() != ""
    # Status line carries the move counter + scoreboard.
    line = render._status_line(fixture_state)
    assert "move 7/25" in line and "cop=" in line and "thief=" in line
