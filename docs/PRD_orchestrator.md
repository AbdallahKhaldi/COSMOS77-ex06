# PRD — Orchestrator / MCP Client (the Game Engine)

> **Module:** `src/cosmos77_ex06/orchestrator/` (+ `src/cosmos77_ex06/agents/`)
> **Acceptance coverage:** **E3** (Server/Client separation), **E4** (free natural-language communication under partial observability), **E5** (fully autonomous pipeline) — also feeds **E6** (cloud URLs), **E7** (report trigger), **E13** (Technical-Loss reruns).
> **Status:** Phase 4 (CORE) of the playbook; depends on Phase 2 (`game/`) and Phase 3 (`mcp_servers/`).
> **The graded statement:** the grade is the **orchestration** — two autonomous agents conversing in **free natural language** over **MCP** under **partial observability** — not the pursuit strategy. This module *is* that orchestration. It is where the project earns or loses its marks.

---

## 1. Purpose and scope

The orchestrator is the **MCP Client** and the **game engine** in one. It is the only place in the codebase that:

1. holds an **LLM** (Google **Gemini**, `gemini-2.5-flash`, via the `google-genai` SDK);
2. opens **FastMCP Client** sessions to the two MCP servers (cop + thief) and authenticates with **token auth**;
3. drives the **per-turn loop** that turns a partial observation + the opponent's last natural-language message into the next agent action;
4. advances the authoritative board through MCP tool calls and **records the full transcript** (every natural-language message, every tool call, every resulting board state);
5. orchestrates the higher rhythm: `num_games` sub-games, each `≤ max_moves`, with **Technical-Loss** voiding and re-running so exactly 6 valid sub-games complete with **zero manual intervention**.

This is the embodiment of **Dec-POMDP control**: a centralized engine that nonetheless feeds each agent *only* its private, partial observation, and lets the two agents coordinate exclusively through text they emit and read.

### Out of scope (owned elsewhere)

- Grid rules, capture, scoring, sub-game/game bookkeeping → `game/` (PRD_game).
- The two FastMCP servers and their tools → `mcp_servers/` (PRD_mcp_servers).
- The natural-language *protocol design* (message semantics, ambiguity, deception) → PRD_nl_protocol.
- Decision heuristics / optional Q-Table → `strategy/` (PRD_strategy).
- The report JSON + Gmail send (the cop triggers it at game end) → `report/` (PRD_report).

### Files (all under the 150-line cap; rule 1)

| File | Responsibility |
|---|---|
| `agents/base.py` | `BaseAgent`: builds the per-turn prompt from a **partial** observation + the opponent's last NL message; defines role-agnostic framing. |
| `agents/cop.py` / `agents/thief.py` | `CopAgent` / `ThiefAgent`: role-specific system framing + goal. Subclass `BaseAgent` (rule 3, no duplication). |
| `orchestrator/engine.py` | `GameEngine`: owns the two FastMCP Clients, the `GameState`, and the sub-game/game loop. |
| `orchestrator/turn.py` | `play_turn(...)`: a single agent's turn (prompt → Gemini → NL message + tool call → board update → record). Split out to keep `engine.py` ≤ 150 lines. |
| `orchestrator/gemini_client.py` | `GeminiClient`: thin wrapper over `google-genai`; **structured-output JSON decisions** executed by the engine via the MCP server tools; routes every call through the **Gatekeeper**; retries free-tier 429/5xx with backoff. |
| `orchestrator/transcript.py` | Append-only transcript recorder (NL message + tool call + board snapshot per turn). |
| `orchestrator/runner.py` | (Phase 7) full-game driver: `num_games` sub-games + Technical-Loss reruns + report assembly. |

The SDK (rule 2) exposes `SDK.run_local_game()` / `SDK.run_full_game()`; the CLI, GUI, and tests call **only** the SDK, never the engine internals directly.

---

## 2. The architectural boundary (E3) — non-negotiable

```
            ┌──────────────────────────── ORCHESTRATOR (MCP Client) ────────────────────────────┐
            │                                                                                    │
            │   GeminiClient (LLM lives HERE)  ── reads ─►  partial obs + opponent NL message     │
            │        │  ask()                                                                     │
            │        ▼                                                                            │
            │   GameEngine / turn loop ── routes chosen tool call ──┐                              │
            │        │  records transcript                          │                              │
            └────────┼──────────────────────────────────────────── │ ──────────────────────────┘
                     │ FastMCP Client (token auth)                  │ FastMCP Client (token auth)
                     ▼                                              ▼
        ┌────────────────────────┐                    ┌────────────────────────┐
        │  COP FastMCP server     │                    │  THIEF FastMCP server   │
        │  TOOLS ONLY — NO LLM    │                    │  TOOLS ONLY — NO LLM    │
        │  send_message,          │                    │  send_message,          │
        │  receive_messages,      │                    │  receive_messages,      │
        │  get_local_observation, │                    │  get_local_observation, │
        │  apply_move,            │                    │  apply_move,            │
        │  place_barrier (cop),   │                    │  verify_position        │
        │  verify_position        │                    │                         │
        └────────────────────────┘                    └────────────────────────┘
```

**Rule (graded, enforced in QA, Phase 12):** nothing under `mcp_servers/` may import or call an LLM. The servers execute *tools*; the **orchestrator** is the only thing that *thinks*. A static check in the acceptance audit greps `mcp_servers/` for `genai`/`gemini`/`anthropic`/`openai` and fails if any appear. This boundary is exactly what the spec rewards: a clean **MCP Server/Client separation** where intelligence is the client and capability is the server.

---

## 3. The per-turn loop (E4) — the heart of the engine

A *turn* is one agent acting once. Per `turn_order: ["thief", "cop"]`, the **thief moves first**, then the cop. The loop for a single agent's turn (`turn.play_turn`) is:

1. **Pull the partial observation.** Call the agent's own MCP server tool `get_local_observation(role)`. The server returns **only** what that role is allowed to see — its own position and the cells within its vision radius — **never** the opponent's exact cell. This is the `Ωᵢ`/`O` of the Dec-POMDP: each agent perceives a private, partial slice of the true state.
2. **Pull the opponent's last message.** Call `receive_messages()` to get the latest **free natural-language** utterance the other agent emitted on the previous turn (taunts, claimed observations, hedges, or deliberate **deception**). On the very first turn there is none.
3. **Build the prompt** (`BaseAgent.build_prompt`). Assemble: the role framing (cop = capture; thief = survive 25 moves), the rules summary (grid size, diagonal allowed, barriers cop-only, capture = cop lands on the thief's cell — all sourced from `config`, never hardcoded), the agent's **partial observation**, the **opponent's last NL message**, and an instruction to (a) *reason* about where the opponent likely is given the text and the partial view, (b) emit one **free-language message** to the opponent (it may bluff), and (c) commit to exactly one action by calling a movement/barrier tool.
4. **Ask Gemini with native MCP tool-calling** (§4). The model returns a natural-language message **and** selects a tool. The engine logs and routes that tool call.
5. **Execute the chosen tool** against **that agent's** MCP server: `apply_move(role, direction)`, or `place_barrier(role)` for the cop. The agent's NL message is published with `send_message(role, content)` so the opponent can read it next turn.
6. **Advance the board.** The server applies the move/barrier to the authoritative `GameState`. The engine then asks `game/rules` whether this turn produced a **capture** (cop on thief's cell) or hit the **move limit** (thief survives at `max_moves`).
7. **Record everything** (`transcript.append`): turn number, role, the NL message, the tool name + arguments, the resulting board snapshot (positions + barriers + move counter), and the MCP server URL the call hit. This transcript is graded evidence (E10/E11) and the raw material for the report (E7).

A *sub-game* repeats turns (thief, then cop) until capture or the move limit, capped at `max_moves`. A *game* is `num_games` valid sub-games.

### Sequence (one full turn)

```
GameEngine ─► get_local_observation(thief) ─► thief server ─► partial view
GameEngine ─► receive_messages()           ─► thief server ─► cop's last NL message
ThiefAgent.build_prompt(view, cop_message)
GeminiClient.ask(prompt, thief_session)    ─► NL message + tool selection
GameEngine routes ─► send_message(thief, "...") + apply_move(thief, "NE")
                  ─► thief server updates GameState
game.rules.check(state) ─► (continue | capture | move_limit)
transcript.append(turn=k, role=thief, msg, tool, args, board, url)
   ... then the cop's turn, symmetrically ...
```

---

## 4. Gemini structured-output decisions, engine-routed MCP execution (the LLM call lives here)

We use **structured-output decisions executed via the MCP server tools by the engine** (Server/Client separation + MCP tool use preserved), **not** the SDK's `tools=[session]` native-MCP mechanism. Reason: **google-genai 2.9.0 deep-copies the `GenerateContentConfig` for every request, and a live FastMCP `ClientSession` holds an `_asyncio.Future` that cannot be deep-copied** (`TypeError: cannot pickle '_asyncio.Future' object`). So a live MCP session in `tools=[...]` is unusable in this SDK version.

Instead, the engine asks Gemini for a single JSON object via `response_mime_type="application/json"` + a role-conditional `response_schema`: a free natural-language `message` plus an `action` (the COP's action enum allows `["move", "barrier"]`; the THIEF's allows `["move"]` only). The engine then logs, validates, and executes that action against the correct server (`apply_move` / `place_barrier`). MCP tool use is therefore still real — the engine routes every decision through the FastMCP tools — and every tool decision passes through `turn.py` (recorded in the transcript, attributed to the right MCP URL) for full observability. The coordinate guard (`guard.py`) still scans every outgoing `message`.

```python
from google.genai import types

action = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "type": types.Schema(type=types.Type.STRING, enum=role_actions),   # cop: move|barrier; thief: move
        "direction": types.Schema(type=types.Type.STRING, enum=DIRECTIONS),
        "x": types.Schema(type=types.Type.INTEGER),
        "y": types.Schema(type=types.Type.INTEGER),
    },
    required=["type"],
)
schema = types.Schema(
    type=types.Type.OBJECT,
    properties={"message": types.Schema(type=types.Type.STRING), "action": action},
    required=["message", "action"],
)
config = types.GenerateContentConfig(
    temperature=cfg.llm.temperature,            # from config (default 0.2)
    response_mime_type="application/json",
    response_schema=schema,                      # NO tools, NO live session, NO AFC field
)
response = await client.aio.models.generate_content(
    model=cfg.llm.model, contents=prompt, config=config,
)
decision = json.loads(response.text)            # {"message": ..., "action": {"type", "direction"|"x","y"}}
```

The async path (`client.aio.models.generate_content`) is retained, with config-driven retries (`llm.max_retries`, `llm.retry_base_seconds`) for transient free-tier 429/5xx errors. The free-language `message` is recorded and relayed to the opponent next turn (E4); the engine maps `action` → `apply_move`/`place_barrier` and routes it through the agent's MCP server.

**Server/Client separation (restated):** this `generate_content` call — the only LLM call in the system — sits in `gemini_client.py` inside the orchestrator. The MCP servers never call it; they only expose the tools Gemini chooses among.

### The Gatekeeper (rule 13)

Every `GeminiClient.ask(...)` routes through `shared/gatekeeper.py`, which meters token/cost per call and scrubs secrets (its regex already masks `AIza…` Gemini keys) from any logged payload. Conversations are short (a few hundred tokens per turn) so cost is effectively zero, but it is **always measured** — the gatekeeper is the single audited choke point for LLM I/O.

---

## 5. Partial observability and the NL inference moment (E4)

The engine never hands an agent the opponent's coordinates. The only channels through which the thief can learn where the cop is — and vice versa — are:

1. its **own partial observation** (`get_local_observation`), and
2. the **opponent's free natural-language message** (`receive_messages`).

So the prompt explicitly asks the model to *infer* the opponent's likely cell from the text. Example exchange the engine records:

- Cop → "I'm sweeping the north-east quadrant; I think I saw movement near the top edge."
- Thief reads it, reasons "the cop is probably committing to the NE; I'll slip toward the SW corner," and emits "Nothing up here, all quiet" — a **deliberate deception** while moving the opposite way.

The engine does not parse or constrain these strings. There is **no rigid numeric protocol**: messages are arbitrary text, and the receiving agent's LLM is solely responsible for interpretation. The transcript captures at least one such *inference-from-partial-observation* moment per game, which the README (E11) and the Phase 12 free-language check require.

---

## 6. The gatekeeper routing and tool dispatch

"Gatekeeper" here has two distinct meanings the engine keeps separate:

- **LLM gatekeeper** (`shared/gatekeeper.py`, §4) — metering/secret-scrub for Gemini calls.
- **Tool routing** (engine-level) — when auto-calling is disabled, `turn.py` receives the model's proposed `(tool_name, args)` and routes it to the **correct** FastMCP Client by role. The cop's tool calls go only to the cop server (with `COP_MCP_TOKEN`/`ORCHESTRATOR_TOKEN`); the thief's only to the thief server. The router rejects a tool the role may not use (e.g. a thief proposing `place_barrier`) and re-prompts (§7), and it validates moves against `game/moves.legal_moves` before applying. This keeps every action legal, attributed, and recorded — the orchestration stays autonomous and auditable.

All four credentials (`COP_MCP_TOKEN`, `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN`, and the connection URLs) come from env + `config.yaml` (rule 4 / E8). Token rotation immediately **revokes** access (the servers use FastMCP `StaticTokenVerifier`), satisfying the revocable-auth requirement of E6.

---

## 7. Free-tier rate-limit and robustness handling

Gemini's free tier enforces RPM/RPD quotas, and the native-MCP integration is experimental. The engine is built to ride this out **without manual intervention** (E5):

- **Tight prompts.** Prompts are kept short (partial observation + one prior message + terse rules) to minimize tokens and stay under quota. Dev runs use small grids and few moves (`--grid 3`, `--games 1`).
- **Backoff + retry.** `GeminiClient.ask` catches `429`/`RESOURCE_EXHAUSTED` and transient `5xx`, then retries with capped exponential backoff and jitter. The retry budget is config-driven.
- **Malformed / no-tool responses.** If the model returns prose but selects no valid tool, the engine **re-prompts once** with an explicit "you must call exactly one movement tool" instruction. If it still fails, the turn is a **Technical-Loss** condition for that sub-game (§8), not a crash.
- **Deterministic in tests (rule 6/17).** The whole `google-genai` + FastMCP `Client` surface is **mocked** in the unit suite — no live Gemini, no live MCP, no network in CI. `random` is seeded; prompts and positions are fixed. Live end-to-end runs are tagged with the `live` pytest marker and excluded via `-m 'not live'`.

---

## 8. Driving `num_games` sub-games + Technical-Loss reruns (E5, E13)

The full-game rhythm (Phase 7, `orchestrator/runner.py`) is:

```
valid = 0
while valid < cfg.num_games:                  # default 6
    result = engine.play_sub_game()           # ≤ cfg.max_moves turns, thief first
    if result.technical_loss:                 # network/LLM/tool failure mid-sub-game
        transcript.note_void(result)          # void it, do NOT count it
        continue                              # re-run a fresh sub-game
    totals.accumulate(result)                 # scoring from config table
    valid += 1
report = builder.build_internal_game(totals, transcript)   # §9.1 schema
# the COP agent triggers the Gmail JSON send at game end (E7, PRD_report)
```

- A **valid** sub-game ends in a clean capture (cop_win 20 / thief_loss 5) or a clean survival at `max_moves` (thief_win 10 / cop_loss 5), per the config scoring table.
- A **Technical-Loss** is a sub-game that fails *technically* — a dropped MCP connection, an exhausted Gemini quota that survives all retries, a persistent invalid-tool loop. Per E13 it is **voided** (never scored) and a **fresh sub-game is re-run** until exactly `num_games` valid sub-games complete. The void is noted in the transcript for transparency but excluded from totals.
- The loop is fully autonomous from `init → 6 valid sub-games → report`, with **no human in the loop** — the defining property of E5.

The same engine targets **local** servers (`http://localhost:8001|8002/mcp`) or **cloud** servers (Horizon `https://*.fastmcp.app/mcp` or a `cloudflared` tunnel) by reading `mcp.cop_url`/`mcp.thief_url` from config; a `--cloud` flag swaps the URL set (E6). Deployment is **platform-agnostic** per the spec ("Prefect Cloud or a similar platform" + tunnels): cloudflared is the simple installed default, Prefect Horizon / FastMCP Cloud is the hosted option.

---

## 9. The transcript (graded evidence)

`orchestrator/transcript.py` keeps an append-only record. Each entry:

```json
{
  "sub_game": 2,
  "turn": 7,
  "role": "thief",
  "nl_message": "All quiet up north, nothing to see.",
  "tool": "apply_move",
  "args": {"role": "thief", "direction": "SW"},
  "board": {"cop": [1, 4], "thief": [3, 0], "barriers": [[2, 2]], "move": 7},
  "mcp_url": "https://thief-xxxx.fastmcp.app/mcp"
}
```

The transcript is the source for: the GUI replay (E10), the CLI logs proving valid **cloud-MCP** comms (E10/E11), the example NL exchanges in the README (E11), and the per-sub-game records folded into the internal-game JSON (E7, schema §9.1). It must show genuine **free natural language** (not a numeric protocol) and at least one inference-under-partial-observability moment.

---

## 10. Configuration surface (rule 4 / E8)

Everything the engine needs is read through `shared/config.py` from `config/config.yaml` — nothing hardcoded:

| Key | Used for |
|---|---|
| `grid_size`, `max_moves`, `num_games`, `max_barriers`, `allow_diagonal`, `turn_order` | rules summary in the prompt + loop bounds + turn order (thief first) |
| `scoring.{cop_win, thief_win, cop_loss, thief_loss}` | totals accumulation |
| `llm.{provider, model, temperature}` | the Gemini call |
| `mcp.{cop_url, thief_url, cop_port, thief_port}` | which servers the Client connects to (local vs cloud) |
| `report.{to, timezone}` | the cop's end-of-game email (E7) |
| env: `GEMINI_API_KEY`, `COP_MCP_TOKEN`, `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN` | LLM key + token auth (gitignored; `.env.example` only, rule 9) |

---

## 11. Testing strategy (rules 6, 7, 17)

All LLM/MCP/network I/O is mocked; the suite is deterministic and offline.

- **Loop correctness** — with mocked agent decisions, the engine runs N sub-games; assert thief-then-cop order, capture ends a sub-game, the move limit yields thief survival.
- **E3 separation** — assert Gemini is invoked by the **engine/client**, never by anything under `mcp_servers/`; a static grep test fails if an LLM import appears in a server file.
- **E4 free language** — assert each turn produces a non-empty `nl_message` field that is not a bare coordinate string (proves free language, not a numeric protocol).
- **E13 Technical-Loss** — inject a simulated mid-sub-game failure; assert the sub-game is voided, not scored, and a rerun fires until `num_games` valid sub-games complete.
- **Rate-limit handling** — mock a `429`; assert backoff/retry, then a re-prompt-once path, then graceful Technical-Loss if still failing.
- **Transcript completeness** — assert every recorded turn has role, NL message, tool + args, board snapshot, and MCP URL.

Live runs (`-m live`) are the human verification path:

```bash
uv run cosmos77-pursuit run --local --games 1 --grid 3   # one tiny end-to-end sub-game
uv run cosmos77-pursuit run --local --games 6            # full autonomous local game
uv run cosmos77-pursuit run --cloud  --games 1           # same pipeline over public HTTPS URLs
```

---

## 12. Acceptance mapping

| Criterion | How this module satisfies it |
|---|---|
| **E3** Server/Client separation | LLM lives only in `gemini_client.py`/`engine.py`; servers expose tools only; enforced by static check. |
| **E4** Free NL under partial observability | Per-turn prompt = partial obs + opponent's last NL message; model infers position; messages are arbitrary text (incl. deception). |
| **E5** Fully autonomous pipeline | `runner.py` drives init → `num_games` valid sub-games → report with no manual steps; backoff/re-prompt keep it self-healing. |
| **E6** Local → cloud | Same engine reads `mcp.*_url` from config; `--cloud` swaps to Horizon/tunnel URLs with token auth. |
| **E7** Automated report trigger | At game end the cop agent triggers the JSON Gmail send (built by `report/`, fed by the transcript/totals). |
| **E8** Config-driven | All bounds, scoring, model, URLs, tokens via `config.yaml`/env; nothing hardcoded. |
| **E13** Technical-Loss handling | Failed sub-games voided and re-run until exactly `num_games` valid sub-games complete. |

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Gemini free-tier quota exhaustion mid-game | Short prompts; small dev grids; capped exponential backoff + jitter; voided-and-rerun as last resort (E13). |
| Native MCP integration is experimental | Support engine-routed mode (auto-calling disabled) so every tool call is validated/logged by us, not implicitly by the SDK. |
| Model emits prose but no valid tool | Re-prompt once with an explicit "call exactly one movement tool" instruction; then Technical-Loss, never a crash. |
| Cloud cold-start / dropped MCP connection | Treated as Technical-Loss → void + rerun; tunnel URLs re-read from config each run (free tunnels rotate). |
| Accidental LLM creep into a server | Phase 12 static grep over `mcp_servers/`; CI fails on any LLM import there (protects E3). |
| Numeric-protocol drift (E4 violation) | Test asserts NL messages are not bare coordinates; prompt forbids structured numeric handshakes. |
