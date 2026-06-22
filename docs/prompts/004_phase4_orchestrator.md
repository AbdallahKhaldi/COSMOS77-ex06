# Prompt log — Phase 4: Orchestrator + Gemini natural-language loop (E3, E4, E5)

The graded CORE: the orchestrator (MCP Client) + the Gemini native-MCP tool-calling loop.
Real google-genai 2.9.0 is wired; the unit suite mocks it. Built via build → adversarial
review → fix; the review caught two live-run-only defects (below) that mocked CI could not.

## What was built
- `agents/base.py` — `BaseAgent` builds the per-turn prompt from the role's PARTIAL observation
  + the opponent's last NL message, instructing the LLM to (a) infer the opponent's likely cell,
  (b) emit a FREE NL message (landmarks only, no coordinates, may bluff), (c) choose one
  move/barrier action. `BaseAgent.interpret` produces a private belief `{seen, opponent_cell,
  heard, credibility}` (the partial-observability inference, E4). `CopAgent`/`ThiefAgent` +
  `make_agent` factory. No LLM call here.
- `orchestrator/gemini_client.py` — wraps google-genai; **async** `ask(role, prompt, mcp_session)`
  builds `GenerateContentConfig(tools=[mcp_session], temperature, automatic_function_calling=
  AutomaticFunctionCallingConfig(disable=True))` and awaits **`client.aio.models.generate_content`**
  (see critical fix #1), parses `.text` + `.function_calls`, meters tokens through the Gatekeeper
  (in-memory accumulator, recorded once per call). Dependency-injectable `client_factory`
  (lazy real-client construction `# pragma: no cover`).
- `orchestrator/turn.py` — one agent's turn: observe → read opponent message (engine-held) →
  build prompt → ask Gemini → run the coordinate guard → route the chosen tool to the right MCP
  client → record. Async.
- `orchestrator/guard.py` — `CoordinateGuard` (config-driven `nl_guard.coord_patterns`) scans every
  outgoing NL message and blocks coordinate-shaped tokens, enforcing free-language-only (E4).
- `orchestrator/engine.py` — `GameEngine`: owns the two FastMCP clients, the authoritative
  GameState, the agents, the GeminiClient; runs the thief→cop loop up to `max_moves`, `num_games`
  sub-games, full transcript; forces forward progress after each full move (fixes the cop-barrier
  infinite loop). The engine is the E4 message RELAY via the transcript — process-independent.
- `orchestrator/transcript.py` — append-only turn records + void notes (E13).
- `orchestrator/local.py` — `run_local_game`/`build_engine`; in-memory FastMCP clients against the
  real cop/thief servers. SDK `run_local_game()` wired; CLI `run --local --games N --grid G`.

## Real google-genai 2.9.0 API (verified by reading the installed source; no live call)
- `genai.Client(api_key=...)`; **`await client.aio.models.generate_content(model=, contents=, config=)`**.
- `types.GenerateContentConfig(tools=[...], temperature, automatic_function_calling, response_schema,
  response_mime_type, system_instruction)`.
- Native MCP tool-calling: pass the live `fastmcp.Client.session` (a real `mcp.ClientSession`) in
  `tools=[...]`. A bare object fails pydantic validation; a real session validates — so the unit
  tests drive a REAL in-memory `ClientSession`, proving the genuine native-MCP path.
- `AutomaticFunctionCallingConfig(disable=True)` → engine-routed mode (full transcript observability).
- Response: `.text`, `.function_calls` (`FunctionCall.name`/`.args`), `.usage_metadata.total_token_count`.

## Adversarial review — two CRITICAL catches (fixed, re-greened)
1. **Live-run crash the mock hid (genai sync vs async).** `ask` used the SYNCHRONOUS
   `client.models.generate_content` while passing an MCP `ClientSession` in `tools=[...]`.
   google-genai 2.9.0 raises `UnsupportedFunctionError("MCP sessions are not supported in
   synchronous methods.")` *before* AFC handling — CI was green (Gemini mocked) but the first real
   call would crash. **Fix:** `ask` is now async and awaits `client.aio.models.generate_content`.
2. **Cloud-safety of the NL relay.** The server-side `send_message` relay made cross-agent delivery
   depend on shared server memory. **Fix:** removed it; the engine-held `Transcript.last_from_opponent`
   is now the SOLE, process-independent relay. (A deeper *observation/state-sync* gap for two
   separate server processes remains and is deferred to Phase 8 — see [[hw6-cloud-state-sync]].)
   Also added: the coordinate guard (free-NL, E4), `BaseAgent.interpret` belief (partial-obs, E4),
   and a Gatekeeper read-modify-write fix.

## Test seam & verification
`GeminiClient(client_factory=...)` injects a fake genai client returning scripted `.text` +
`.function_calls`; the FastMCP layer is the REAL in-memory `Client` against the REAL servers —
proving the LLM is invoked by the engine and the servers only execute tools (E3). Static
`test_servers_import_no_llm` greps `mcp_servers/` for LLM imports. **195 passed, 99.16% coverage**;
ruff/format/line-cap clean. Live agent-vs-agent run is the `GEMINI_API_KEY` touchpoint.
