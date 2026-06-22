# Prompt log — Phase 4: Orchestrator + Gemini natural-language loop (E3, E4, E5)

The graded CORE: the orchestrator (MCP Client) + the Gemini decision loop. Built via
build → adversarial review → fix, then **validated with a real Gemini game** (which is the only
thing that can catch live-only defects — see the two below). All gates green; the unit suite mocks
Gemini, but the pipeline is proven end-to-end against the live API.

## Architecture (final)
- `agents/base.py` — `BaseAgent.build_prompt` builds the per-turn prompt from the role's PARTIAL
  observation + the opponent's last NL message, asking the model for ONE JSON object: a FREE
  natural-language `message` (intentions/observations/bluff — landmarks only, no coordinates) plus
  an `action`. `BaseAgent.interpret` produces a private belief `{seen, opponent_cell, heard,
  credibility}` (partial-observability inference, E4). `CopAgent`/`ThiefAgent` + `make_agent`.
- `orchestrator/gemini_client.py` — **async** `ask(role, prompt)` calls
  `await client.aio.models.generate_content` with **structured output**
  (`response_mime_type="application/json"` + a role-conditional `response_schema`: the cop's action
  enum allows `["move","barrier"]`, the thief's `["move"]`). Parses the JSON decision, maps it to
  `{tool, args}` (`apply_move`/`place_barrier`), meters tokens through the Gatekeeper, and **retries
  transient 429/5xx with backoff** (`llm.max_retries`, `llm.retry_base_seconds`). Dependency-
  injectable `client_factory` (real SDK lazy + `# pragma: no cover`).
- `orchestrator/turn.py` — one agent's turn: observe → read opponent message (engine-held) →
  build prompt → `ask` Gemini → coordinate guard → **route the chosen action to the role's FastMCP
  client** (`apply_move`/`place_barrier`) → record. The LLM decides; the MCP server executes (E3).
- `orchestrator/{engine,transcript,local,guard}.py` — `GameEngine` owns the two FastMCP clients,
  the authoritative GameState, the agents, the GeminiClient; runs thief→cop up to `max_moves`,
  `num_games` sub-games, full transcript; forces forward progress (fixes the cop-barrier infinite
  loop). The engine-held `Transcript` is the SOLE, process-independent NL relay (cloud-safe).
- `SDK.run_local_game()` + CLI `run --local --games N --grid G`.

## Why structured output instead of `tools=[client.session]`
The playbook suggested native MCP tool-calling (`tools=[session]`). Two live-only defects forced a
better design — **the engine already routes every action through the MCP server tools**, so the LLM
only needs to *decide*; it does not need the live session:
1. **(found by the adversarial review)** google-genai 2.9.0 raises `UnsupportedFunctionError` if an
   MCP session is passed to the SYNCHRONOUS `generate_content`. → use the async `aio` path.
2. **(found by the first real run)** even async, passing the live `ClientSession` in `tools=[...]`
   crashes with `TypeError: cannot pickle '_asyncio.Future'` because google-genai **deep-copies the
   request config** and the session holds a Future. → **drop the live session entirely**; ask for a
   structured JSON `{message, action}` decision and let the engine execute the action via
   `apply_move`/`place_barrier` on the role's FastMCP client. Server/Client separation (E3), MCP tool
   use, and free-NL (E4) are all preserved; see [[hw6-cloud-state-sync]] for the deferred Phase-8 item.

## Live validation (real Gemini, key in .env)
`run --local --games 1 --grid 2` and `--grid 3` both complete with no traceback; totals
`{cop:20, thief:5}`. Gatekeeper ledgers confirm real calls (`gemini-2.5-flash`, token counts).
Sample transcript (genuine free language with a bluff, `coord_flagged=False`):
- thief: *"I am not in a corner, I am moving to the center of the board."* (bluff)
- cop: *"Your words are misleading, I see you clearly in the opposite corner."*

**Rate limits:** the free tier caps generate_content requests per short window (observed
`limit: 20`, "retry in ~20s"). The 429 backoff handles bursts; the **Phase-7 full game** (6 sub-games,
many calls) needs pacing + `retryDelay`-respecting retry and modest grids — tracked for Phase 7.

## Test seam & gates
`GeminiClient(client_factory=...)` injects a fake whose `aio.models.generate_content` returns the
JSON decision in `.text`; the FastMCP layer is the REAL in-memory `Client` against the REAL servers
(proves the LLM is invoked by the engine and the servers only execute tools). Static
`test_servers_import_no_llm` greps `mcp_servers/` for LLM imports. **224 passed, 99.20%**;
ruff/format/line-cap clean.
