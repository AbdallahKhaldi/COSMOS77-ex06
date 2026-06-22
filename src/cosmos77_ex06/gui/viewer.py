"""The pygame viewer lifecycle + the headless off-screen PNG renderer (E10/G4).

Two entry points (PRD_gui §2/§4/§6):

* :class:`GameViewer` — an INTERACTIVE window the SDK drives one frame per turn.
  It is **headless-safe**: if no display can be initialised (CI, SSH, the dummy
  driver, or ``GUI_HEADLESS=1``) it enters a no-op mode so the autonomous
  pipeline (E5) never blocks on a screen. Key ``S`` saves a screenshot to
  ``assets/``; ``Q`` / window-close quits the viewer without aborting the game.
* :func:`render_state_to_png` — a pure HEADLESS renderer: it forces the dummy
  SDL video driver, draws a :class:`GameState` onto an off-screen surface via
  ``render.py``, and writes a PNG. No display is ever needed, so screenshots can
  be produced programmatically (the README evidence + the test path).

``pygame`` is imported lazily inside methods (marked ``# pragma: no cover`` where
a real screen would be required) so importing this module is cheap and the suite
runs without a window.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cosmos77_ex06.gui import render
from cosmos77_ex06.gui.theme import Theme
from cosmos77_ex06.shared.config import Config


def _display_available() -> bool:
    """True if a usable display is likely present (probe before opening a window)."""
    if os.environ.get("GUI_HEADLESS") == "1":
        return False
    if os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy":
        return False
    if os.name == "posix" and os.uname().sysname == "Linux":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def render_state_to_png(state: Any, path: Path | str, config: Config | None = None) -> Path:
    """Render ``state`` to an off-screen surface and write a PNG to ``path`` (G4).

    Sets ``SDL_VIDEODRIVER=dummy`` so no display is required, draws via
    ``render.py``, and saves the image. Returns the written path.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame

    theme = Theme.from_config(config or Config())
    if not pygame.get_init():
        pygame.init()
    size = render.board_pixels(theme, state.grid_size)
    surface = pygame.Surface(size)
    render.render_state(surface, theme, state)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(out))
    return out


class GameViewer:
    """Interactive per-turn window; no-op when no display is available (G4)."""

    def __init__(self, config: Config | None = None, *, force_headless: bool | None = None) -> None:
        self.config = config or Config()
        self.theme = Theme.from_config(self.config)
        self.assets_dir = self.config.repo_assets()
        headless = force_headless if force_headless is not None else not _display_available()
        self.enabled = not headless
        self.surface: Any = None
        self.clock: Any = None
        if self.enabled:
            self._open_window()

    def _open_window(self) -> None:  # pragma: no cover - needs a real display
        """Open the pygame window + clock (interactive path only)."""
        import pygame

        try:
            pygame.init()
            self.surface = pygame.display.set_mode((600, 600))
            pygame.display.set_caption(self.theme.caption)
            self.clock = pygame.time.Clock()
        except pygame.error:
            self.enabled = False

    def update(self, state: Any) -> None:
        """Draw one frame for ``state`` and pump events (no-op when headless)."""
        if not self.enabled:
            return
        self._render_and_pump(state)  # pragma: no cover - needs a real display

    def _render_and_pump(self, state: Any) -> None:  # pragma: no cover - real display
        """Resize if needed, render the frame, handle keys, and tick the clock."""
        import pygame

        size = render.board_pixels(self.theme, state.grid_size)
        if self.surface.get_size() != size:
            self.surface = pygame.display.set_mode(size)
        render.render_state(self.surface, self.theme, state)
        pygame.display.flip()
        self._handle_events(state)
        self.clock.tick(self.theme.fps)

    def _handle_events(self, state: Any) -> None:  # pragma: no cover - real display
        """Screenshot on the screenshot key, quit on the quit key / window close."""
        import pygame

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
            elif event.type == pygame.KEYDOWN:
                name = pygame.key.name(event.key)
                if name == self.theme.screenshot_key:
                    self.save_screenshot(state)
                elif name == self.theme.quit_key:
                    self.close()

    def save_screenshot(self, state: Any) -> Path | None:
        """Save the current frame to ``assets/`` (no-op when headless)."""
        if not self.enabled or self.surface is None:
            return None
        return self._save(state)  # pragma: no cover - needs a real display

    def _save(self, state: Any) -> Path:  # pragma: no cover - needs a real display
        """Write the live surface to a turn-stamped PNG under ``assets/``."""
        import pygame

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        out = self.assets_dir / f"frame_move{state.move_number:03d}.png"
        pygame.image.save(self.surface, str(out))
        return out

    def close(self) -> None:
        """Tear down pygame cleanly (safe to call when headless / already closed)."""
        if not self.enabled:
            return
        self.enabled = False
        import pygame  # pragma: no cover - needs a real display

        pygame.quit()  # pragma: no cover - needs a real display
