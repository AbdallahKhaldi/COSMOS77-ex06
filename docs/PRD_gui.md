# PRD — GUI (pygame Real-Time Viewer) + CLI Comms Logs

**Component:** `src/cosmos77_ex06/gui/` + the orchestrator's structured logging
**Acceptance criterion:** **E10** — *"GUI showing the game in real time + CLI logs proving valid comms with the cloud MCP servers."*
**Supporting criteria:** E11 (GUI screenshots + cloud-MCP CLI logs are embedded as scientific evidence), E4 (the viewer surfaces the **free natural-language** messages so the orchestration is visible), E6 (the CLI log records the **cloud MCP server URL** of every call).
**Phase:** 6 (playbook §8). **Source state:** `game/state.py::GameState`.

> **Context.** HW6 is graded on the **orchestration** — two autonomous agents (a Cop and a Thief) talking **free natural language** over two **FastMCP servers** under **partial observability**, driven by a Gemini-backed orchestrator/MCP-Client (**Server/Client separation**: the LLM never lives in `mcp_servers/`). The GUI and the CLI logs are not the product; they are the **observability layer** that *proves* the autonomous Dec-POMDP pipeline ran. The viewer makes the live pursuit watchable for screenshots; the structured CLI logs are the auditable, text-only evidence that the orchestrator really exchanged messages and tool calls with the (cloud) MCP servers. Neither component contains game logic or an LLM — both are **pure consumers** of `GameState` and the orchestrator's emitted events.

---

## 1. Goals & non-goals

### Goals
- **G1.** Render the board, the Cop, the Thief, and the cop-placed **barriers** in real time, one frame per turn, read directly from `GameState`.
- **G2.** Display the **latest free natural-language message** from each agent (Cop and Thief), so a viewer can watch the conversation, not just the pieces — this is the visible face of E4.
- **G3.** Provide a **screenshot key** that saves the current frame to `assets/` for the README (E11).
- **G4.** Be **headless-safe**: when there is no display (CI, SSH, the test suite), skip the window cleanly so nothing requires a screen. The game must run identically with or without the GUI.
- **G5.** Emit **structured per-turn CLI logs** (turn#, role, NL message, tool call, resulting position, **server URL**) that serve as the "CLI logs proving cloud-MCP comms" the README cites.
- **G6.** Be **config-driven** (rule 4): colours, cell pixel size, FPS, window caption, screenshot directory — all read through `shared/config.py` from `config/config.yaml`; nothing hardcoded.

### Non-goals
- No game rules, capture detection, or scoring — those live in `game/` (PRD_game). The viewer never mutates `GameState`.
- No LLM, no MCP client, no network. The GUI imports neither `google-genai` nor `fastmcp`. (Server/Client separation, E3, applies transitively: the visual layer is even further from the model than the servers are.)
- No interactivity that changes the game (no human-controlled pieces). Input is limited to *screenshot* and *quit*. The pipeline is **fully autonomous** (E5); the GUI is a passive observer.
- No headless image rendering pipeline beyond what pygame's dummy driver supports — CI proves logic, not pixels.

---

## 2. Architecture & file layout

The component must obey the **150-line cap** (rule 1), so it splits along a clean view/render seam, and follows the **lazy-heavy-import** discipline (`pygame` imported *inside* functions, marked `# pragma: no cover`, faked in tests):

| File | Responsibility | Cap |
|---|---|---|
| `gui/viewer.py` | `GameViewer` lifecycle: init pygame (or detect headless and no-op), the per-turn `update(state)` call, event handling (screenshot / quit), `close()`. Owns the window + clock. | ≤150 |
| `gui/render.py` | Pure drawing helpers: `draw_grid`, `draw_barriers`, `draw_agent`, `draw_messages`, `cell_rect`. Each takes a surface + `GameState` (or fields) and returns/issues draw calls; **no pygame init, no event loop** — this is the part unit tests assert against. | ≤150 |
| `gui/theme.py` *(optional)* | Resolves colours/sizes/FPS/caption from config into a small typed `Theme` dataclass, so `render.py` stays free of config lookups. | ≤80 |

**Data contract.** The viewer reads only the serializable `GameState` from `game/state.py`: `cop_pos`, `thief_pos`, `barriers` (set of blocked cells), `grid_size`, `move_number`, and a `messages` view giving the **latest** NL message per role. The viewer never reaches into the engine, the agents, or the MCP clients — it is wired in by the SDK:

```
SDK.run_local_game(gui=True)
   └─ GameEngine turn loop
         ├─ (LLM call in orchestrator → tool call → FastMCP server → board update)   # not the GUI's concern
         ├─ engine emits a TurnEvent + advances GameState
         ├─ viewer.update(game_state)          # one frame
         └─ logger.info(structured turn record) # the CLI evidence (§5)
```

The engine drives both the GUI **and** the logging from the same per-turn event, so the screenshot and the CLI log line for a given turn are always consistent (important when both are pasted into the README side by side).

---

## 3. Visual specification (what a frame shows)

A single frame is a faithful snapshot of the Dec-POMDP **global state** (the *viewer* sees ground truth for the human; the *agents* never do — that asymmetry is the whole point of partial observability and is what the README discusses):

1. **The grid** — `grid_size` cells (default 5×5; the sanity ladder may set 2×2…4×4), drawn as a square lattice with thin separators. Cell pixel size from config.
2. **The Cop** — a distinct coloured token (e.g. blue) at `cop_pos`.
3. **The Thief** — a distinct coloured token (e.g. red) at `thief_pos`.
4. **Barriers** — the cop-only blocked cells (≤`max_barriers`, impassable to both), drawn as filled/hatched dark cells so it is visually obvious which routes are cut off.
5. **A capture indicator** — when the Cop lands on the Thief's cell (capture), highlight that cell (this is the moment a sub-game ends with a cop win).
6. **A header / status strip** — `Sub-game k/num_games`, `Move m/max_moves`, current turn role (thief moves first).
7. **The message panel** — a strip (below or beside the grid) showing the **latest free natural-language message from each agent**, prefixed by role, e.g.

   ```
   THIEF: "I'm hugging the eastern wall, staying clear of open ground."
   COP:   "I think you're north-east; I'm cutting off the top-right with a barrier."
   ```

   This panel is the visible proof of E4 — genuine natural language, never a numeric protocol. Long messages are truncated/wrapped to fit; the **full** text always survives in the CLI log (§5) and the transcript.

Colours, fonts, token shapes, panel placement, and FPS are theme values resolved from config — no literals in `render.py`.

---

## 4. Headless-safe behaviour (G4 — mandatory)

The viewer must **never require a screen**. Three layers guarantee this:

1. **Display probe at init.** `GameViewer.__init__` (or a `enabled` factory) checks for a usable display before creating a window. If none is available — no `DISPLAY`/`WAYLAND_DISPLAY` on Linux, or pygame's display init fails — the viewer enters a **no-op mode**: `update()`, screenshot, and `close()` all become safe no-ops, and the game proceeds exactly as if `gui=False`. The autonomous pipeline (E5) is never blocked waiting on a window.

2. **Dummy SDL driver for CI / tests.** When tests *do* want to exercise the pygame code paths without a screen, they set `SDL_VIDEODRIVER=dummy` (and `SDL_AUDIODRIVER=dummy`) in the environment before pygame init. With the dummy driver, pygame initialises against an off-screen surface, so `draw_*` calls and even `save_screenshot` work without a physical display. This is the documented mechanism the test suite uses (see `tests/conftest.py` / the GUI test fixture) so **tests need no screen**.

   ```python
   # conftest fixture sketch
   os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
   os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
   ```

3. **Lazy import + fakes.** `import pygame` happens inside the viewer methods (marked `# pragma: no cover`), so the heavy GUI dependency is not pulled in during ordinary CI runs, and unit tests inject a fake pygame to assert on draw calls (rule 6 — all GUI I/O mocked; rule 17 — deterministic, no flakes).

A `--gui` CLI flag and the SDK's `gui=True` argument simply *request* the window; the headless probe decides whether it actually materialises. Default is **off** (the autonomous/cloud runs and CI run headless).

---

## 5. Structured CLI comms logs (E10 — the "proof of cloud-MCP comms")

This is the second, equally-graded half of E10 and the evidence E11 embeds. Independently of whether the GUI is on, **the orchestrator emits one structured log record per agent action**, routed through `shared/logging_setup.py`. These lines are the audit trail that the two autonomous agents really conversed over the MCP servers — and, in a cloud run, over **public HTTPS MCP URLs**.

### 5.1 Required fields per turn record

Every per-turn log line MUST carry, at minimum:

| Field | Meaning | Why it matters |
|---|---|---|
| `turn` | Global turn counter (and `sub_game` index) | Reconstruct the ≤25-move, 6-sub-game timeline (E1, E13) |
| `role` | `thief` or `cop` (thief moves first) | Shows correct turn order |
| `message` | The **full** free natural-language message the agent emitted | Proof of E4 — natural language, not numerics; partial-observation inference / bluffing is visible here |
| `tool_call` | The MCP tool invoked + arguments (e.g. `apply_move(role="thief", direction="NE")`, `place_barrier(...)`, `get_local_observation(...)`) | Proof the LLM acted **via the server's tools**, not by mutating state directly (Server/Client separation, E3) |
| `resulting_position` | The agent's cell after the move (or `captured` / `blocked`) | Ties the conversation to the board state |
| `server_url` | The **MCP server URL the call hit** — `http://localhost:8001/mcp` locally, the `https://…` cloud URL when `--cloud` | **This is the "cloud-MCP comms" proof** (E6/E10): the line literally shows the public HTTPS endpoint |

Recommended extras: `auth=token:ok` (token-auth succeeded — proves revocable token auth, E2), `latency_ms`, `obs` (the partial view the agent was given), and a `technical_loss` flag when a sub-game is voided and rerun (E13).

### 5.2 Format

Two compatible renderings, selected by config (`logging.format`):
- **Human-readable** (default for terminal capture / screenshots into `assets/`):
  ```
  [sub 2 | turn 014 | THIEF] url=https://cop-xxxx.trycloudflare.com/mcp auth=ok
    msg="Heading for the open south corridor; I don't think you've spotted me."
    tool=apply_move(direction=S) -> pos=(4,1)
  ```
- **JSON Lines** (machine-checkable, used by tests and by anyone diffing a transcript):
  ```json
  {"sub_game":2,"turn":14,"role":"thief","server_url":"https://cop-xxxx.trycloudflare.com/mcp","auth":"ok","message":"Heading for the open south corridor; I don't think you've spotted me.","tool_call":"apply_move(direction=S)","resulting_position":[4,1]}
  ```

### 5.3 Where it comes from

The orchestrator/`GameEngine` produces these records (it is the only component that holds the MCP `server_url`, the token, and the LLM's NL output). `logging_setup` formats them; the **gatekeeper** (rule 13) separately meters the short Gemini calls. The GUI does **not** generate these logs — it consumes the same `GameState`; the engine is the single producer, keeping the screenshot and the log line for a turn consistent. Secrets are scrubbed by the logging layer (the token value is never printed — only `auth:ok`/`token verified`), satisfying rule 9 / E2's revocable-auth intent without leaking the secret.

### 5.4 Capturing it for the README (E11)

A cloud run (`cosmos77-pursuit run --cloud --games 1`) is piped/tee'd to `assets/cloud_mcp_cli_log.txt`; that captured log, showing the `https://*.fastmcp.app/mcp` or `*.trycloudflare.com/mcp` URLs against real NL messages and tool calls, is the graded "CLI logs proving valid comms with the cloud MCP servers."

---

## 6. Screenshot mechanism (G3)

- A keypress (default **`S`**, configurable via `gui.screenshot_key`) calls `save_screenshot()`, which writes the current frame to `assets/` (path from `config.paths.assets`) with a timestamped, sub-game/turn-stamped filename, e.g. `assets/frame_sub2_turn14.png`.
- Under the **dummy SDL driver**, the save still works (off-screen surface), so a headless run can optionally auto-emit a few key frames for the README without a screen.
- A small set of saved frames (start, a barrier being placed, a capture) are the GUI screenshots the README embeds (E11). `assets/*` is kept in git (per the Phase-0 `.gitignore`), so the images ship with the repo.
- Default **`Q`** / window-close quits the viewer cleanly (`close()` → `pygame.quit()`); quitting the viewer does **not** abort the autonomous game — the engine keeps running headless.

---

## 7. Configuration keys (proposed `config/config.yaml` additions)

All under a `gui:` / `logging:` block, read via `shared/config.py` (rule 4, E8). No values appear in code.

```yaml
gui:
  enabled: false          # default off; --gui or SDK gui=True requests it; headless probe has final say
  cell_size: 96           # pixels per grid cell
  fps: 2                  # turn-paced; one frame per turn, slow enough to watch
  caption: "COSMOS77-ex06 — Cops & Robbers over MCP"
  screenshot_key: "s"
  quit_key: "q"
  colors:                 # theme; resolved into render.py
    background: [18, 18, 24]
    grid_line:  [60, 60, 70]
    cop:        [60, 130, 240]
    thief:      [230, 70, 70]
    barrier:    [40, 40, 40]
    capture:    [250, 210, 60]
    text:       [235, 235, 235]
  message_lines: 2        # how many wrapped lines per agent message in the panel

logging:
  format: "human"         # "human" | "jsonl"
  show_server_url: true   # MUST be true so cloud-MCP comms are provable (E10/E6)
  show_full_message: true # never truncate the NL message in the log (only the GUI panel truncates)
```

---

## 8. Testing strategy (rule 6, 7, 17)

All GUI/log tests are deterministic, mock all I/O, and need **no screen** (dummy SDL driver). No live pygame window, no network.

| Test | Asserts | Criterion |
|---|---|---|
| `test_render_draw_calls` | Given a fixture `GameState`, `render.draw_*` issues the expected draw calls (grid cells, cop at `cop_pos`, thief at `thief_pos`, one barrier per blocked cell) — against a **fake pygame** surface. | E10 |
| `test_headless_noop` | With no display available, `GameViewer` enters no-op mode: `update()`/`screenshot()`/`close()` raise nothing and the game still completes. | G4 / E5 |
| `test_dummy_driver_init` | With `SDL_VIDEODRIVER=dummy`, pygame init + an off-screen `save_screenshot` succeed without a physical display. | G4 |
| `test_message_panel_shows_nl` | The message panel renders the latest NL string per role (non-numeric content present). | E4 |
| `test_log_formatter_fields` | The per-turn log record contains `turn`, `role`, `message`, `tool_call`, `resulting_position`, and **`server_url`**; the human and `jsonl` formats both round-trip. | E10 / E6 |
| `test_log_redacts_token` | The token value is never present in any emitted log line (only `auth:ok`). | rule 9 / E2 |
| `test_screenshot_path` | `save_screenshot` writes into `config.paths.assets` with a turn-stamped name. | G3 |

Tests are tagged so anything that would touch a real display is excluded by default; the suite runs `-m 'not live'` in CI.

---

## 9. Acceptance mapping (E10) & dependencies

- **E10 satisfied when:** (a) `cosmos77-pursuit run --local --games 1 --gui` shows the board, pieces, barriers, and both agents' live NL messages, and `S` saves a frame to `assets/`; **and** (b) a run emits structured CLI logs carrying turn#, role, NL message, tool call, resulting position, and the MCP **server URL**, with a `--cloud` capture proving comms against public HTTPS MCP URLs.
- **Feeds E11:** the saved `assets/*.png` frames and the captured `assets/cloud_mcp_cli_log.txt` are embedded in the scientific Dec-POMDP README as the "GUI screenshots + CLI logs" evidence.
- **Upstream deps:** `game/state.py` (GameState), `orchestrator/engine.py` (per-turn events + `server_url` + NL message), `shared/config.py`, `shared/logging_setup.py`.
- **Invariants honoured:** no LLM/MCP/network in the GUI (E3 transitively); fully config-driven (E8); 150-line cap with `viewer.py`/`render.py` split (rule 1); lazy pygame import + dummy-driver tests (rule 6, 17); the autonomous pipeline never blocks on a window (E5).
