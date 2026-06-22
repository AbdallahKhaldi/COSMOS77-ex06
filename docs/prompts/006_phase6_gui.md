# Phase 6 — GUI (pygame real-time viewer) + structured CLI comms logs (E10)

> Acceptance criterion **E10** — *"GUI showing the game in real time + CLI logs
> proving valid comms with the cloud MCP servers."* Supporting: E4 (the viewer +
> log surface the **free natural-language** messages), E6 (the log carries the
> **MCP server URL** of every call), E11 (the screenshots + captured log are the
> README's scientific evidence). Source state: `game/state.py::GameState`.

## Prompt (paste-in)

Build HW6 Phase 6 — the pygame GUI + structured CLI logs (E10). Pure-ish; the
unit suite must mock/headless pygame (no real display, no network). Do NOT break
any existing test (224 passing) or change game/orchestrator behaviour.

- `gui/render.py` (<=150): PURE drawing helpers over a `GameState` + a pygame
  `Surface` — grid, cop, thief, barriers, latest NL message per agent, scoreboard,
  capture highlight. No window, no display; lazy-import pygame inside functions.
- `gui/viewer.py` (<=150): (1) an INTERACTIVE, headless-safe viewer (key `S`
  screenshots to `assets/`; guards on display init / `SDL_VIDEODRIVER`); (2)
  `render_state_to_png(state, path)` — dummy SDL driver, off-screen Surface,
  writes a PNG with no display.
- Wire `SDK.run_local_game(gui=True)` to drive the interactive viewer alongside
  the engine; `gui=False` default, behaviour unchanged.
- CLI structured logs via `shared/logging_setup`: one record per turn — turn#,
  role, NL message, tool call + args, resulting position, MCP server URL. Wire
  additively into the orchestrator turn. Capture to a file via `--log-file PATH`.
- Generate 3 real sample screenshots by driving the PURE engine through a scripted
  sequence (5x5, barriers, a capture) with injected NL messages.
- Tests under `tests/unit/test_gui/` (dummy SDL / monkeypatch pygame.draw); mark a
  real-display test `live`. Coverage >= 85%.
- Drive all gates green; docstrings + type hints; write this prompt log.

## What was built

| File | Lines | Role |
|---|---|---|
| `src/cosmos77_ex06/gui/render.py` | 126 | pure drawing helpers (grid, agents, barriers, capture, message panel + scoreboard); lazy pygame import |
| `src/cosmos77_ex06/gui/viewer.py` | 144 | `GameViewer` (interactive, headless-safe) + `render_state_to_png` (off-screen PNG) |
| `src/cosmos77_ex06/gui/theme.py` | 83 | resolves the `gui:` config block into a typed `Theme` (rule 4 — no literals in render) |
| `src/cosmos77_ex06/gui/driver.py` | 38 | bridges the live engine `on_turn` hook to the viewer (syncs latest NL per role from the transcript) |
| `src/cosmos77_ex06/orchestrator/turn_log.py` | 75 | structured per-turn comms-log builder/formatter (`human` + `jsonl`; token-redacted) |
| `scripts/generate_sample_screenshots.py` | 73 | deterministic scripted run -> 3 PNGs in `assets/` |

Changed (additive): `orchestrator/turn.py` (emit the log per turn),
`orchestrator/engine.py` (optional `on_turn` hook), `orchestrator/local.py`
(`gui=` -> attach a headless-safe viewer), `sdk/sdk.py` (`gui` passthrough),
`cli/main.py` (`--log-file`), `shared/config.py` (`repo_assets()`),
`config/config.yaml` (`gui:` + `logging:` blocks).

## Headless safety + the PNG path

- `_display_available()` returns False under `GUI_HEADLESS=1`, when
  `SDL_VIDEODRIVER=dummy`, or on Linux without `DISPLAY`/`WAYLAND_DISPLAY`. The
  `GameViewer` then enters no-op mode: `update`/`save_screenshot`/`close` do
  nothing, so the autonomous pipeline (E5) never blocks on a window.
- `render_state_to_png` sets `SDL_VIDEODRIVER=dummy`, inits pygame, draws onto an
  off-screen `pygame.Surface`, and saves a PNG — no display needed. This is the
  key capability behind the sample screenshots and the test path.

## Per-turn log format (sample)

Human (default; `logging.format: human`):

```
[sub 2 | turn 014 | THIEF] url=https://cop-xxxx.fastmcp.app/mcp auth=ok
  msg="Heading for the open south corridor; I don't think you've spotted me."
  tool=apply_move(direction=S) -> pos=(4, 1)
```

JSON Lines (`logging.format: jsonl`): the same record with sorted keys; the auth
token value is never printed (only `auth=ok`).

## Sample screenshots (committed)

`assets/gui_start.png`, `assets/gui_midgame.png`, `assets/gui_capture.png` —
produced with `uv run python scripts/generate_sample_screenshots.py`. They show
the start positions, two cop barriers mid-game, and the capture highlight, each
with both agents' live NL messages and the scoreboard.

## Gates

`ruff check` clean; `ruff format --check` clean; line cap OK (all <=150);
`pytest -q -m 'not live'` green at 98% coverage; the existing 224 tests still
pass and `gui` defaults off.
