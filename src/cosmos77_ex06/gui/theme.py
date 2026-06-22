"""Resolve GUI colours/sizes/FPS/caption from config into a typed ``Theme``.

Keeps ``render.py`` free of config lookups (rule 4 / E8): no colour or pixel
literal ever appears in the drawing code — every visual value is read here from
the ``gui:`` block of ``config/config.yaml`` via :class:`Config`, with safe
defaults so the tiny inline test configs (which omit ``gui:``) still build.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cosmos77_ex06.shared.config import Config

Color = tuple[int, int, int]

_DEFAULTS: dict[str, Any] = {
    "cell_size": 96,
    "panel_height": 132,
    "fps": 2,
    "caption": "COSMOS77-ex06 — Cops & Robbers over MCP",
    "screenshot_key": "s",
    "quit_key": "q",
    "message_lines": 2,
    "colors": {
        "background": [18, 18, 24],
        "grid_line": [60, 60, 70],
        "cell": [30, 30, 38],
        "cop": [60, 130, 240],
        "thief": [230, 70, 70],
        "barrier": [40, 40, 40],
        "capture": [250, 210, 60],
        "text": [235, 235, 235],
    },
}


@dataclass(frozen=True)
class Theme:
    """Immutable resolved visual settings consumed by ``render.py``."""

    cell_size: int
    panel_height: int
    fps: int
    caption: str
    screenshot_key: str
    quit_key: str
    message_lines: int
    background: Color
    grid_line: Color
    cell: Color
    cop: Color
    thief: Color
    barrier: Color
    capture: Color
    text: Color

    @classmethod
    def from_config(cls, config: Config) -> Theme:
        """Build a :class:`Theme` from the ``gui:`` config block (defaults filled)."""
        colors = dict(_DEFAULTS["colors"])
        colors.update(config.get("gui.colors", default={}) or {})
        return cls(
            cell_size=int(config.get("gui.cell_size", default=_DEFAULTS["cell_size"])),
            panel_height=int(config.get("gui.panel_height", default=_DEFAULTS["panel_height"])),
            fps=int(config.get("gui.fps", default=_DEFAULTS["fps"])),
            caption=str(config.get("gui.caption", default=_DEFAULTS["caption"])),
            screenshot_key=str(
                config.get("gui.screenshot_key", default=_DEFAULTS["screenshot_key"])
            ),
            quit_key=str(config.get("gui.quit_key", default=_DEFAULTS["quit_key"])),
            message_lines=int(config.get("gui.message_lines", default=_DEFAULTS["message_lines"])),
            background=tuple(colors["background"]),
            grid_line=tuple(colors["grid_line"]),
            cell=tuple(colors["cell"]),
            cop=tuple(colors["cop"]),
            thief=tuple(colors["thief"]),
            barrier=tuple(colors["barrier"]),
            capture=tuple(colors["capture"]),
            text=tuple(colors["text"]),
        )
