"""Pure drawing helpers for the Cops & Robbers viewer (PRD_gui §2/§3, E10).

Every function takes a pygame ``Surface`` plus a :class:`GameState` (or fields)
and a :class:`Theme`; none of them open a window, init the display, or run an
event loop, so they work headless against an off-screen surface (the dummy SDL
driver). ``pygame`` is imported lazily INSIDE the functions so importing this
module never pulls the heavy GUI dependency, and the suite can fake the draw
calls. The viewer (ground truth) renders the global Dec-POMDP state; the agents
never see this — that asymmetry is the whole point of partial observability.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.gui.theme import Theme


def cell_rect(theme: Theme, col: int, row: int) -> tuple[int, int, int, int]:
    """Return the ``(x, y, w, h)`` pixel rectangle for grid cell ``(col, row)``."""
    size = theme.cell_size
    return (col * size, row * size, size, size)


def board_pixels(theme: Theme, grid_size: list[int]) -> tuple[int, int]:
    """Return the full ``(width, height)`` window size incl. the message panel."""
    cols, rows = int(grid_size[0]), int(grid_size[1])
    return (cols * theme.cell_size, rows * theme.cell_size + theme.panel_height)


def draw_grid(surface: Any, theme: Theme, grid_size: list[int]) -> None:
    """Fill the background and draw the empty cell lattice with separators."""
    import pygame

    cols, rows = int(grid_size[0]), int(grid_size[1])
    surface.fill(theme.background)
    for row in range(rows):
        for col in range(cols):
            rect = cell_rect(theme, col, row)
            pygame.draw.rect(surface, theme.cell, rect)
            pygame.draw.rect(surface, theme.grid_line, rect, 1)


def draw_barriers(surface: Any, theme: Theme, barriers: list[tuple[int, int]]) -> None:
    """Draw each cop-placed barrier as a filled dark cell (impassable to both)."""
    import pygame

    for col, row in barriers:
        pygame.draw.rect(surface, theme.barrier, cell_rect(theme, col, row))


def draw_agent(surface: Any, theme: Theme, pos: tuple[int, int], color: tuple) -> None:
    """Draw one agent token as a filled circle centred in its cell."""
    import pygame

    size = theme.cell_size
    cx = pos[0] * size + size // 2
    cy = pos[1] * size + size // 2
    pygame.draw.circle(surface, color, (cx, cy), max(4, size // 3))


def draw_capture(surface: Any, theme: Theme, pos: tuple[int, int]) -> None:
    """Highlight the capture cell (cop landed on the thief — sub-game ends)."""
    import pygame

    pygame.draw.rect(surface, theme.capture, cell_rect(theme, *pos), 4)


def _font(size: int) -> Any:
    """Build a default pygame font at ``size`` px (font subsystem inits lazily)."""
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
    return pygame.font.Font(None, size)


def _blit_line(surface: Any, theme: Theme, text: str, x: int, y: int, size: int) -> None:
    """Render one line of theme-coloured text onto ``surface`` at ``(x, y)``."""
    surface.blit(_font(size).render(text, True, theme.text), (x, y))


def draw_messages(surface: Any, theme: Theme, state: Any) -> None:
    """Draw the latest free NL message per role + the scoreboard (E4 evidence)."""
    cols = int(state.grid_size[0])
    top = int(state.grid_size[1]) * theme.cell_size
    import pygame

    pygame.draw.rect(
        surface, theme.background, (0, top, cols * theme.cell_size, theme.panel_height)
    )
    y = top + 6
    for role in ("thief", "cop"):
        text = _latest_message(state, role)
        _blit_line(surface, theme, f"{role.upper()}: {text}", 8, y, 22)
        y += 26
    _blit_line(surface, theme, _status_line(state), 8, y, 22)


def _latest_message(state: Any, role: str) -> str:
    """The most recent message authored by ``role`` (empty string if none)."""
    for entry in reversed(state.messages):
        if entry.get("role") == role:
            return str(entry.get("text", ""))
    return ""


def _status_line(state: Any) -> str:
    """A header strip: move counter, current role, scoreboard."""
    scores = state.scores
    return (
        f"move {state.move_number}/{state.max_moves}  "
        f"turn={state.current_role}  "
        f"cop={scores.get('cop', 0)} thief={scores.get('thief', 0)}"
    )


def render_state(surface: Any, theme: Theme, state: Any) -> None:
    """Draw a full frame for ``state`` onto ``surface`` (grid, pieces, panel)."""
    draw_grid(surface, theme, state.grid_size)
    draw_barriers(surface, theme, [tuple(b) for b in state.barriers])
    draw_agent(surface, theme, tuple(state.thief_pos), theme.thief)
    draw_agent(surface, theme, tuple(state.cop_pos), theme.cop)
    if tuple(state.cop_pos) == tuple(state.thief_pos):
        draw_capture(surface, theme, tuple(state.cop_pos))
    draw_messages(surface, theme, state)
