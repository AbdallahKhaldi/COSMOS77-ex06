"""Generate deterministic sample GUI screenshots — no LLM, no network (E10/E11).

Drives the PURE game engine (``SDK.new_game`` / ``SDK.step``) through a short
SCRIPTED sequence of legal moves on a 5x5 board with a couple of cop barriers and
a capture, injecting illustrative free natural-language messages into
``GameState.messages``, then uses the headless :func:`render_state_to_png` (dummy
SDL driver) to write three frames to ``assets/``. These prove the renderer works
and give the README real GUI images now; Phase-7 regenerates them from a real
transcript. Run: ``uv run python scripts/generate_sample_screenshots.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cosmos77_ex06.gui.viewer import render_state_to_png  # noqa: E402
from cosmos77_ex06.sdk.sdk import SDK  # noqa: E402


def _say(state, turn: int, role: str, text: str) -> None:
    """Inject one illustrative free natural-language message for the panel."""
    state.add_message(turn, role, text)


def build_frames(sdk: SDK) -> list[tuple[str, object]]:
    """Script a 5x5 sub-game (barriers + a capture) and return named snapshots."""
    state = sdk.new_game(cop_start=(4, 4), thief_start=(0, 0))
    _say(state, 0, "thief", "Starting in the north-west, I'll hug open ground.")
    _say(state, 0, "cop", "I'll sweep down from the south-east and pin you.")
    frames = [("gui_start", _copy(state))]

    sdk.step(state, "cop", ("barrier", (2, 2)))
    sdk.step(state, "cop", ("barrier", (3, 2)))
    sdk.step(state, "thief", ("move", "SE"))
    sdk.step(state, "cop", ("move", "NW"))
    state.move_number = 7
    _say(state, 7, "thief", "Those barriers cut my eastern escape; sliding south.")
    _say(state, 7, "cop", "Routes are closing — I think you're mid-board, closing in.")
    frames.append(("gui_midgame", _copy(state)))

    state.thief_pos = (2, 3)
    state.cop_pos = (2, 4)
    sdk.step(state, "cop", ("move", "N"))
    state.move_number = 12
    _say(state, 12, "thief", "Cornered against the wall, nowhere left to run.")
    _say(state, 12, "cop", "Gotcha — landed on your cell. Capture!")
    frames.append(("gui_capture", _copy(state)))
    return frames


def _copy(state):
    """Deep-copy the GameState via its deterministic dict round-trip."""
    from cosmos77_ex06.game.state import GameState

    return GameState.from_dict(state.to_dict())


def main() -> int:
    """Render the scripted frames to ``assets/`` and report the written files."""
    sdk = SDK()
    assets = sdk.config.repo_assets()
    for name, state in build_frames(sdk):
        out = render_state_to_png(state, assets / f"{name}.png", sdk.config)
        print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
