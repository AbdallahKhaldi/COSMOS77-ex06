# docs/TODO.md — COSMOS77-ex06 granular backlog

> HW6 — Dual AI-agent Cops & Robbers over MCP servers · Orchestration of AI Agents (203.3763).
> The grade is the **orchestration** (two autonomous agents talking **free natural language** over MCP
> under partial observability), not the game strategy. Server/Client separation (the LLM lives ONLY in
> the orchestrator/MCP-Client, never in `mcp_servers/`) is graded. Everything config-driven via
> `config/config.yaml`. Acceptance criteria E1–E13 (playbook §1.5) are referenced per task.
>
> **Format contract.** Every task is one line that STARTS with a zero-padded `T-NNNN ` id token, so
> `grep -c '^T-' docs/TODO.md` counts them. Pattern: `T-NNNN [P<phase>][<area>] <imperative>`.
> Ids run sequentially from T-0001 with no gaps. Phases group under `## Phase N — <title>` headers.
> Vocabulary in play: Dec-POMDP, partial observability, MCP Server/Client separation, FastMCP, free
> natural language, orchestration, token auth, Technical-Loss, Prefect Horizon, Cloudflare Tunnel.

## Phase 0 — Bootstrap + tooling (reuse HW1–HW5)

T-0001 [P0][scaffold] Create the full directory tree under src/cosmos77_ex06 (game, agents, mcp_servers, orchestrator, strategy, gui, deploy, report, bonus, cli, sdk, shared).
T-0002 [P0][scaffold] Create tests/ tree with unit/ and integration/ subpackages plus conftest.py placeholder.
T-0003 [P0][scaffold] Create docs/ tree with prompts/ subfolder for the per-phase prompt logs (rule 12).
T-0004 [P0][scaffold] Create config/, assets/, reports/, results/ output directories with .gitkeep where empty.
T-0005 [P0][git] Run git init -b main and set local user.name/user.email for Abdallah Khaldi (no AI co-author trailers).
T-0006 [P0][git] Add the origin remote https://github.com/AbdallahKhaldi/COSMOS77-ex06.git (set-url if it exists).
T-0007 [P0][scaffold] Port pyproject.toml from HW5: rename package cosmos77_ex05 -> cosmos77_ex06, version 1.00.
T-0008 [P0][scaffold] Set authors (Abdallah Khaldi, Tasneem Natour) and requires-python >=3.11,<3.12 in pyproject.toml.
T-0009 [P0][deps] Declare runtime deps: fastmcp>=3.4, google-genai, pyyaml, pydantic>=2.6, rich, pygame, matplotlib, numpy.
T-0010 [P0][deps] Declare Gmail deps: google-api-python-client, google-auth-oauthlib, google-auth-httplib2, python-dotenv.
T-0011 [P0][deps] Declare dev deps: pytest, pytest-cov, pytest-mock, pytest-asyncio, ruff, hypothesis, pre-commit.
T-0012 [P0][scaffold] Register CLI entry point cosmos77-pursuit = cosmos77_ex06.cli.main:main in [project.scripts].
T-0013 [P0][scaffold] Port ruff config (line-length 100, target py311, select E/F/W/I/N/UP/B/C4/SIM, ignore E501).
T-0014 [P0][scaffold] Port coverage config (branch=true, fail_under=85) scoped to src/cosmos77_ex06.
T-0015 [P0][scaffold] Port pytest config and add asyncio_mode = "auto" for pytest-asyncio.
T-0016 [P0][scaffold] Define the live pytest marker so real-I/O tests can be excluded via -m 'not live'.
T-0017 [P0][scaffold] Create .python-version pinning 3.11.
T-0018 [P0][scaffold] Write .gitignore: .env, .venv/, __pycache__/, .ruff_cache/, .coverage, .DS_Store, credentials.json, token.json, *.token, *.pdf.
T-0019 [P0][scaffold] Ensure .gitignore KEEPS assets/*, reports/*.json, config/config.yaml tracked.
T-0020 [P0][secrets] Write .env.example with GEMINI_API_KEY, COP_MCP_TOKEN, THIEF_MCP_TOKEN, ORCHESTRATOR_TOKEN placeholders (no real values, rule 9).
T-0021 [P0][config] Author config/config.yaml with grid_size [5,5], max_moves 25, num_games 6, max_barriers 5 (E8).
T-0022 [P0][config] Add allow_diagonal true and turn_order ["thief","cop"] (thief first) to config.yaml.
T-0023 [P0][config] Add scoring block cop_win 20, thief_win 10, cop_loss 5, thief_loss 5 to config.yaml.
T-0024 [P0][config] Add llm block provider gemini, model gemini-2.5-flash, temperature 0.2 to config.yaml.
T-0025 [P0][config] Add mcp block cop_url/thief_url/cop_port 8001/thief_port 8002 to config.yaml.
T-0026 [P0][config] Add report block to rmisegal+uoh26b@gmail.com, timezone Asia/Jerusalem to config.yaml.
T-0027 [P0][config] Add group block name COSMOS77 and github_repo URL to config.yaml.
T-0028 [P0][config] Add paths block results/reports/assets to config.yaml.
T-0029 [P0][shared] Port shared/version.py verbatim with VERSION = "1.00".
T-0030 [P0][shared] Port shared/gatekeeper.py verbatim (token/cost meter; secret-scrub regex covers AIza Gemini keys).
T-0031 [P0][shared] Adapt shared/config.py to load YAML config/config.yaml (replace HW5 JSON loader).
T-0032 [P0][shared] Keep generic config accessors get/env/paths/version/from_path; drop HW5 domain accessors.
T-0033 [P0][shared] Port shared/logging_setup.py with HW6 namespace default and copy config/logging_config.json.
T-0034 [P0][shared] Add a structured-logging helper that includes turn#, role, NL message, tool call, server URL.
T-0035 [P0][sdk] Port sdk/sdk.py skeleton (Config + Gatekeeper owned, lazy intra-method imports, one method per stage).
T-0036 [P0][sdk] Stub SDK methods new_game, step, run_local_game, run_full_game, report so signatures exist early.
T-0037 [P0][scaffold] Create constants.py for role names ("cop","thief") and direction enums sourced from config where possible.
T-0038 [P0][scaffold] Add src/cosmos77_ex06/__init__.py exporting __version__ from version.py.
T-0039 [P0][docs] Write CLAUDE.md verbatim from playbook §17 (17 rules + architecture rule + vocabulary).
T-0040 [P0][docs] Write README.md placeholder noting it is filled in Phase 10 (Dec-POMDP scientific README).
T-0041 [P0][docs] Add LICENSE (port from HW5).
T-0042 [P0][docs] Add CHANGELOG.md seeded with the 1.00 entry.
T-0043 [P0][docs] Add CONTRIBUTING.md (port from HW5).
T-0044 [P0][tooling] Port scripts/check_line_cap.py (package-agnostic, 150-line cap, rule 1).
T-0045 [P0][tooling] Port scripts/generate_cover_pdf.py and retarget _REPO_URL to COSMOS77-ex06 (final fields in Phase 13).
T-0046 [P0][tooling] Port .pre-commit-config.yaml pinning ruff 0.15.18 in lockstep with uv.lock and CI.
T-0047 [P0][ci] Port .github/workflows/ci.yml: uv sync --frozen, ruff check, ruff format --check, check_line_cap.
T-0048 [P0][ci] Add CI pytest step pytest -m 'not live' --cov=src/cosmos77_ex06 --cov-fail-under=85 (no network, no GUI).
T-0049 [P0][tooling] Run uv sync and commit uv.lock.
T-0050 [P0][qa] Run uv run ruff check . and confirm zero violations.
T-0051 [P0][qa] Run uv run python scripts/check_line_cap.py and confirm zero offenders.
T-0052 [P0][qa] Run pre-commit install and verify hooks fire on a test commit.
T-0053 [P0][test] Add a smoke test importing cosmos77_ex06 and asserting __version__ == "1.00".
T-0054 [P0][test] Add a config-load smoke test asserting grid_size/scoring/mcp read from config.yaml.
T-0055 [P0][docs] Save docs/prompts/000_phase0_bootstrap.md prompt log.
T-0056 [P0][docs] Update docs/TODO.md (this file) at end of phase and reference task ids in commits.
T-0057 [P0][git] Make multiple conventional commits (chore: scaffold, build: deps, ci: workflow) referencing TODO ids.
T-0058 [P0][git] Push to origin main and confirm GitHub Actions is green.

## Phase 1 — Mandatory docs (PRD/PLAN/TODO + mechanism PRDs)

T-0059 [P1][docs] Write docs/PRD.md context section (203.3763 L09, distributed multi-agent, MCP, grade = orchestration not strategy).
T-0060 [P1][docs] In PRD.md restate the spec §4 research/report questions to be answered in the README.
T-0061 [P1][docs] Map every functional requirement in PRD.md to acceptance criteria E1–E13.
T-0062 [P1][docs] Document PRD.md non-functional reqs: full autonomy, public reachability, free natural language, English.
T-0063 [P1][docs] List PRD.md KPIs: 6 valid sub-games autonomous, two token-auth MCP servers, cloud URLs, automated Gmail JSON, Dec-POMDP README, >=85% coverage, >=600 TODOs.
T-0064 [P1][docs] Write docs/PRD_game.md: coordinates, diagonal moves, barrier placement (cop only, <=max_barriers, impassable to both).
T-0065 [P1][docs] In PRD_game.md define capture (cop lands on thief cell) and thief survival (25 moves reached).
T-0066 [P1][docs] In PRD_game.md define turn order (thief then cop), sub-game (<=25 moves) vs game (6 sub-games), scoring table — all config-driven (E1, E8).
T-0067 [P1][docs] In PRD_game.md describe the 4-stage sanity ladder 2x2 -> 3x3 -> 4x4 -> 5x5.
T-0068 [P1][docs] Write docs/PRD_mcp_servers.md: two FastMCP servers cop_server.py + thief_server.py (E2).
T-0069 [P1][docs] In PRD_mcp_servers.md enumerate tools: send_message, receive_messages, get_local_observation, verify_position, apply_move, place_barrier.
T-0070 [P1][docs] In PRD_mcp_servers.md specify HTTP transport on separate ports + StaticTokenVerifier revocable token auth.
T-0071 [P1][docs] In PRD_mcp_servers.md assert the server holds NO LLM and leaks NO ground-truth opponent position (E3).
T-0072 [P1][docs] Write docs/PRD_orchestrator.md: the MCP Client / game engine per-turn loop (E3, E5).
T-0073 [P1][docs] In PRD_orchestrator.md describe asking Gemini with native MCP tools (tools=[client.session]) given partial observation + opponent's last NL message.
T-0074 [P1][docs] In PRD_orchestrator.md state the Server/Client separation: the LLM call lives in the orchestrator, servers only execute tools.
T-0075 [P1][docs] Write docs/PRD_nl_protocol.md: free natural-language messaging (intentions, observations, deception) — no rigid numeric protocol (E4).
T-0076 [P1][docs] In PRD_nl_protocol.md document ambiguity handling and how mutual understanding is checked under partial observability.
T-0077 [P1][docs] Write docs/PRD_strategy.md: heuristic (Manhattan/Chebyshev) core + optional tabular Q-Table (RL optional per spec) (E9).
T-0078 [P1][docs] In PRD_strategy.md state whether Gemini decides directly or consults the strategy as a suggested-action tool, and why.
T-0079 [P1][docs] Write docs/PRD_gui.md: pygame real-time viewer (grid, cop, thief, barriers, latest messages) + CLI logs (E10).
T-0080 [P1][docs] Write docs/PRD_deploy.md: local separate ports -> public HTTPS (platform-agnostic; Cloudflare Tunnel default, Prefect Horizon hosted option) (E6).
T-0081 [P1][docs] In PRD_deploy.md document the firewall/public-reachability requirement and token revocation.
T-0082 [P1][docs] Write docs/PRD_report.md: internal-game JSON builder (schema §9.1) + Gmail-API sender (cop triggers, JSON-only body) (E7).
T-0083 [P1][docs] In PRD_report.md document Technical-Loss handling (void + rerun to 6 valid sub-games) (E13).
T-0084 [P1][docs] Write docs/PRD_bonus.md: role-swap series, bonus_game JSON schema (§9.2), mutual_agreement, canonical serializer, mismatch -> 0 (E12).
T-0085 [P1][docs] Write docs/PRD_dec_pomdp.md: the tuple <n, S, {Ai}, P, R, {Omega_i}, O, gamma> defined for THIS game.
T-0086 [P1][docs] In PRD_dec_pomdp.md define state space (positions + barriers) and observation space (partial/local view) explicitly.
T-0087 [P1][docs] Write docs/PLAN.md C4 context + container diagram (orchestrator, two FastMCP servers, Gemini, Gmail).
T-0088 [P1][docs] Add to PLAN.md a sequence diagram of one turn (orchestrator -> Gemini -> tool_call -> FastMCP server -> board update -> opponent NL message).
T-0089 [P1][docs] Write ADR-001 in PLAN.md: FastMCP + google-genai native MCP (no LangChain).
T-0090 [P1][docs] Write ADR-002 in PLAN.md: Gemini free tier gemini-2.5-flash (short conversations).
T-0091 [P1][docs] Write ADR-003 in PLAN.md: platform-agnostic deploy (Cloudflare Tunnel default, Prefect Horizon option).
T-0092 [P1][docs] Write ADR-004 in PLAN.md: heuristic core + optional Q-Table.
T-0093 [P1][docs] Write ADR-005 in PLAN.md: Server/Client separation (LLM only in orchestrator).
T-0094 [P1][docs] Write ADR-006 in PLAN.md: config-driven, zero hardcoding.
T-0095 [P1][docs] Write ADR-007 in PLAN.md: 150-line per-file cap.
T-0096 [P1][docs] Write the PLAN.md risk register: cloud cold-starts, firewall, NL ambiguity, bonus JSON mismatch with mitigations.
T-0097 [P1][docs] Produce docs/TODO.md with >=600 granular tasks distributed across P0–P13 (this file).
T-0098 [P1][qa] Verify grep -c '^T-' docs/TODO.md returns the expected count.
T-0099 [P1][qa] Verify ls docs/PRD_*.md count matches the planned mechanism PRDs.
T-0100 [P1][qa] Verify grep -c 'ADR-' docs/PLAN.md returns >=7.
T-0101 [P1][docs] Cross-link every PRD to its acceptance criterion and owning phase.
T-0102 [P1][docs] Save docs/prompts/001_phase1_docs.md prompt log.
T-0103 [P1][git] Commit per doc chunk with conventional messages referencing TODO ids and push; confirm CI green.

## Phase 2 — Game logic + rules (pure, fully tested)

T-0104 [P2][game] Create game/board.py Board class reading grid_size from config (E1, E8).
T-0105 [P2][game] Implement Board cell representation and (x,y) position model.
T-0106 [P2][game] Implement Board.in_bounds(pos) respecting configured grid dimensions.
T-0107 [P2][game] Implement Board barrier set storage (blocked cells) and is_blocked(pos).
T-0108 [P2][game] Implement Board.neighbors(pos) including diagonal neighbors when allow_diagonal is true.
T-0109 [P2][game] Keep board.py <=140 lines; split helpers if it grows (rule 1).
T-0110 [P2][game] Create game/moves.py legal_moves(pos, board) excluding out-of-bounds and blocked cells.
T-0111 [P2][game] Implement moves.apply_move(pos, direction) returning the new position.
T-0112 [P2][game] Implement moves.place_barrier(pos) restricted to cop and capped at max_barriers per sub-game.
T-0113 [P2][game] Ensure a placed barrier is impassable for BOTH cop and thief.
T-0114 [P2][game] Define the direction set (orthogonal + diagonal) driven by allow_diagonal config.
T-0115 [P2][game] Keep moves.py <=120 lines.
T-0116 [P2][game] Create game/rules.py capture detection (cop on thief cell).
T-0117 [P2][game] Implement rules thief-survival detection when max_moves is reached.
T-0118 [P2][game] Implement rules turn-order enforcement (thief moves first).
T-0119 [P2][game] Implement rules sub-game result resolution (cop_win vs thief_win).
T-0120 [P2][game] Implement rules scoring lookup from config scoring table.
T-0121 [P2][game] Keep rules.py <=130 lines.
T-0122 [P2][game] Create game/match.py SubGame running up to 25 moves, returning result + per-move log.
T-0123 [P2][game] Implement match.Game running num_games sub-games and accumulating cop/thief totals.
T-0124 [P2][game] Implement Technical-Loss flagging in match (void a sub-game + mark for rerun) (E13).
T-0125 [P2][game] Keep match.py <=140 lines.
T-0126 [P2][game] Create game/state.py serializable GameState (positions, barriers, move#, messages).
T-0127 [P2][game] Make GameState the single object the GUI and report read; keep state.py <=80 lines.
T-0128 [P2][game] Add GameState.to_dict / from_dict for serialization to reports.
T-0129 [P2][sdk] Wire SDK.new_game() to construct a fresh GameState from config.
T-0130 [P2][sdk] Wire SDK.step(...) to advance one move via rules + moves.
T-0131 [P2][game] Add validation that the thief and cop start positions differ.
T-0132 [P2][game] Add a helper to compute Manhattan and Chebyshev distance between positions (shared with strategy).
T-0133 [P2][test] Test capture triggers when the cop lands on the thief cell.
T-0134 [P2][test] Test a barrier blocks both agents (neither can enter a blocked cell).
T-0135 [P2][test] Test the thief wins when max_moves is reached without capture.
T-0136 [P2][test] Test diagonal moves are legal only when allow_diagonal is true.
T-0137 [P2][test] Test scoring matches the table for cop_win/thief_win outcomes.
T-0138 [P2][test] Test a full 6-sub-game game accumulates correct totals.
T-0139 [P2][test] Test a Technical-Loss sub-game is voided and flagged for rerun.
T-0140 [P2][test] Test legal_moves excludes out-of-bounds neighbors at corners and edges.
T-0141 [P2][test] Test place_barrier rejects a sixth barrier when max_barriers is 5.
T-0142 [P2][test] Test place_barrier rejects placement by the thief role.
T-0143 [P2][test] Test turn-order enforcement rejects a cop move before the thief moves.
T-0144 [P2][test] Test GameState round-trips through to_dict/from_dict losslessly.
T-0145 [P2][test] Seed random and fix start positions for deterministic game tests (rule 17).
T-0146 [P2][test] Property-test (hypothesis) that legal_moves never returns blocked or out-of-bounds cells.
T-0147 [P2][qa] Confirm coverage on game/ >= 90%.
T-0148 [P2][qa] Run ruff check . with zero violations for Phase 2 files.
T-0149 [P2][qa] Run check_line_cap on game/ files (all <=150).
T-0150 [P2][docs] Save docs/prompts/002_phase2_game.md prompt log.
T-0151 [P2][git] Commit per game module with conventional messages and push; confirm CI green.

## Phase 3 — Two FastMCP servers + token auth

T-0152 [P3][mcp] Create mcp_servers/tools.py with shared tool implementations operating on a GameState handle (E2).
T-0153 [P3][mcp] Implement tool send_message(role, content) appending a free-language message to GameState.
T-0154 [P3][mcp] Implement tool receive_messages() returning the opponent's recent NL messages.
T-0155 [P3][mcp] Implement tool get_local_observation(role) returning ONLY the partial view that role may see.
T-0156 [P3][mcp] Ensure get_local_observation never leaks the opponent's exact cell (partial observability, E3).
T-0157 [P3][mcp] Implement tool verify_position(x,y) confirming the caller's own occupancy.
T-0158 [P3][mcp] Implement tool apply_move(role, direction) updating GameState through game.moves.
T-0159 [P3][mcp] Implement tool place_barrier(role) (cop-only) updating GameState barriers.
T-0160 [P3][mcp] Split tools.py if it exceeds 150 lines (e.g. tools_cop.py / tools_thief.py / tools_common.py).
T-0161 [P3][mcp] Create mcp_servers/cop_server.py importing FastMCP and registering cop-appropriate tools.
T-0162 [P3][mcp] Create mcp_servers/thief_server.py registering thief-appropriate tools.
T-0163 [P3][mcp] Attach StaticTokenVerifier to cop_server using COP_MCP_TOKEN + ORCHESTRATOR_TOKEN from env.
T-0164 [P3][mcp] Attach StaticTokenVerifier to thief_server using THIEF_MCP_TOKEN + ORCHESTRATOR_TOKEN from env.
T-0165 [P3][mcp] Configure required_scopes=["read"] on both servers' token verifiers.
T-0166 [P3][mcp] Configure mcp.run(transport="http", host="0.0.0.0", port=<config port>) per server using config ports.
T-0167 [P3][mcp] Keep cop_server.py and thief_server.py each <=120 lines.
T-0168 [P3][mcp] Assert no LLM/Gemini import appears anywhere under mcp_servers/ (E3 guard).
T-0169 [P3][mcp] Create mcp_servers/app.py exposing mcp.http_app() ASGI apps for uvicorn/Horizon.
T-0170 [P3][mcp] Lazy-import fastmcp inside server entrypoints (pragma no cover) to keep CI light.
T-0171 [P3][mcp] Read all ports/tokens from config + env, never hardcoded (E8).
T-0172 [P3][test] Test list_tools on cop_server returns the expected cop tool names (FastMCP in-memory Client).
T-0173 [P3][test] Test list_tools on thief_server returns the expected thief tool names.
T-0174 [P3][test] Test get_local_observation returns a PARTIAL view and the opponent's exact position is NOT leaked.
T-0175 [P3][test] Test an unauthenticated client is rejected by both servers.
T-0176 [P3][test] Test a bad-token client is rejected by both servers.
T-0177 [P3][test] Test the ORCHESTRATOR_TOKEN is accepted by both servers.
T-0178 [P3][test] Test apply_move via the tool updates GameState correctly.
T-0179 [P3][test] Test place_barrier via the tool is rejected for the thief role.
T-0180 [P3][test] Test send_message + receive_messages round-trip a free-language string.
T-0181 [P3][test] Mock/in-memory only — no real network in the CI suite (rule 6).
T-0182 [P3][test] Static test grepping mcp_servers/ for forbidden LLM imports to enforce E3.
T-0183 [P3][qa] Confirm coverage gate holds with the new server tests.
T-0184 [P3][qa] Run ruff check and check_line_cap on Phase 3 files.
T-0185 [P3][doc] Document the in-memory FastMCP Client test pattern in PRD_mcp_servers.md.
T-0186 [P3][doc] Document token revocation (rotate COP_MCP_TOKEN/THIEF_MCP_TOKEN to revoke).
T-0187 [P3][docs] Save docs/prompts/003_phase3_servers.md prompt log.
T-0188 [P3][git] Commit per server/tool module and push; confirm CI green.

## Phase 4 — Orchestrator + Gemini natural-language loop (THE CORE)

T-0189 [P4][agents] Create agents/base.py BaseAgent(role, mcp_url, token) (rule 3 base class).
T-0190 [P4][agents] Implement BaseAgent prompt builder from the agent's PARTIAL observation + opponent's last NL message (E4).
T-0191 [P4][agents] Instruct the LLM to reason about the opponent's likely position from text (partial observability).
T-0192 [P4][agents] Instruct the LLM to emit a free-language message (intentions/observations, may bluff) (E4).
T-0193 [P4][agents] Instruct the LLM to choose a move/barrier via a tool call.
T-0194 [P4][agents] Keep base.py <=140 lines.
T-0195 [P4][agents] Create CopAgent subclass with cop-specific framing (pursue + cut off escape).
T-0196 [P4][agents] Create ThiefAgent subclass with thief-specific framing (evade + reach open space).
T-0197 [P4][orch] Create orchestrator/engine.py GameEngine(config) owning the two FastMCP Clients (with tokens) + GameState.
T-0198 [P4][orch] Implement the turn loop: thief turn -> cop turn -> check capture/limit, up to max_moves.
T-0199 [P4][orch] Run num_games sub-games inside the engine.
T-0200 [P4][orch] Record the full transcript (every NL message + tool call + board state) per turn.
T-0201 [P4][orch] Enforce Server/Client separation: the LLM call lives in the engine, servers only execute tools (E3).
T-0202 [P4][orch] Split engine.py + turn.py to keep each <=150 lines.
T-0203 [P4][orch] Create orchestrator/gemini_client.py wrapping google-genai.
T-0204 [P4][orch] Implement gemini_client.ask(role_prompt, mcp_session) returning the agent's NL message + chosen tool action.
T-0205 [P4][orch] Pass the live MCP session into Gemini tools (config tools=[player_client.session]) for native MCP tool-calling.
T-0206 [P4][orch] Route every LLM call through shared/gatekeeper.py (rule 13).
T-0207 [P4][orch] Read model/temperature/key (GEMINI_API_KEY) from config + env, never hardcoded (E8).
T-0208 [P4][orch] Keep gemini_client.py <=120 lines and lazy-import google-genai (pragma no cover).
T-0209 [P4][orch] Decide and implement auto-function-calling vs manual routing so tool calls can be logged through the engine.
T-0210 [P4][orch] Keep dev prompts tight and dev max_moves small to respect free-tier rate limits.
T-0211 [P4][sdk] Wire SDK.run_local_game() to run a full game against local MCP servers, returning transcript + totals.
T-0212 [P4][cli] Add cosmos77-pursuit run --local --games N --grid G CLI subcommand.
T-0213 [P4][test] Test the engine runs N sub-games with mocked agent decisions (mock google-genai + FastMCP Client).
T-0214 [P4][test] Assert a free-language message field is present and non-numeric-only each turn (E4).
T-0215 [P4][test] Assert the LLM is invoked by the engine and NOT by the server (E3).
T-0216 [P4][test] Test a mocked capture ends the sub-game immediately.
T-0217 [P4][test] Test the transcript is complete (every turn has message + tool call + position).
T-0218 [P4][test] Test the gatekeeper records every mocked LLM call.
T-0219 [P4][test] Test the orchestrator attaches the correct token per MCP Client.
T-0220 [P4][test] Test BaseAgent prompt includes only the partial observation, never ground truth.
T-0221 [P4][test] Mock all Gemini/MCP I/O; no live calls in the suite (rule 6).
T-0222 [P4][qa] Run a one-tiny-sub-game live smoke (3x3, 1 game) and confirm NL exchange + movement (manual, live marker).
T-0223 [P4][qa] Confirm coverage gate, ruff, and line cap on Phase 4 files.
T-0224 [P4][docs] Document the natural-language exchange examples captured from the smoke run in PRD_nl_protocol.md.
T-0225 [P4][docs] Save docs/prompts/004_phase4_orchestrator.md prompt log.
T-0226 [P4][git] Commit per orchestrator/agent module and push; confirm CI green.

## Phase 5 — Decision strategy (heuristic + optional Q-Table)

T-0227 [P5][strategy] Create strategy/heuristic.py operating on the agent's ESTIMATE, not ground truth (E9).
T-0228 [P5][strategy] Implement cop heuristic: minimize Manhattan/Chebyshev distance to the estimated thief cell.
T-0229 [P5][strategy] Implement cop barrier heuristic: place a barrier to cut off escape when adjacent.
T-0230 [P5][strategy] Implement thief heuristic: maximize distance / move toward open space.
T-0231 [P5][strategy] Keep heuristic.py <=120 lines and pure (no LLM/MCP).
T-0232 [P5][strategy] Read heuristic tunables from config where applicable (no hardcoding).
T-0233 [P5][strategy] Create strategy/qtable.py tabular Q-Learning (optional extension per spec §8).
T-0234 [P5][strategy] Define Q[state, action] with state = positions and action = move/barrier.
T-0235 [P5][strategy] Implement the Bellman update q += alpha*(r + gamma*max_next - q).
T-0236 [P5][strategy] Implement epsilon-greedy action selection with hyper-params from config.
T-0237 [P5][strategy] Log per-episode rewards to results/ for the learning curve.
T-0238 [P5][strategy] Keep qtable.py <=140 lines.
T-0239 [P5][strategy] Create strategy/plots.py rendering the learning curve to assets/learning_curve.png via matplotlib.
T-0240 [P5][strategy] Keep plots.py <=80 lines and lazy-import matplotlib (pragma no cover).
T-0241 [P5][agents] Wire the strategy as an optional suggested-action tool the LLM may accept or override.
T-0242 [P5][docs] Document in PRD_strategy.md whether Gemini decides directly or consults the suggestion, and why.
T-0243 [P5][test] Test the cop heuristic reduces distance to the estimated thief on a fixture board.
T-0244 [P5][test] Test the thief heuristic increases distance / moves toward open space on a fixture board.
T-0245 [P5][test] Test the cop barrier heuristic places a barrier when adjacent to the estimate.
T-0246 [P5][test] Test the Q-Table update matches the Bellman formula on a hand-computed example.
T-0247 [P5][test] Test epsilon-greedy explores vs exploits as configured (seeded RNG).
T-0248 [P5][test] Test the heuristic operates on the estimate input, not ground truth.
T-0249 [P5][test] Test plots.py is skipped gracefully when no Q-Table episode log exists.
T-0250 [P5][test] Seed RNG for deterministic strategy tests (rule 17).
T-0251 [P5][qa] Confirm coverage gate, ruff, and line cap on Phase 5 files.
T-0252 [P5][docs] Save docs/prompts/005_phase5_strategy.md prompt log.
T-0253 [P5][git] Commit per strategy module and push; confirm CI green.

## Phase 6 — GUI + CLI logs

T-0254 [P6][gui] Create gui/viewer.py pygame grid viewer drawing board, cop, thief, barriers (E10).
T-0255 [P6][gui] Render the latest natural-language message from each agent on screen.
T-0256 [P6][gui] Update the viewer each turn from GameState.
T-0257 [P6][gui] Add a screenshot key (S) that saves the current frame to assets/.
T-0258 [P6][gui] Make the viewer headless-safe (skip the window when no display, e.g. CI / SDL_VIDEODRIVER=dummy).
T-0259 [P6][gui] Split viewer.py + render.py to keep each <=150 lines.
T-0260 [P6][gui] Lazy-import pygame inside the viewer (pragma no cover).
T-0261 [P6][gui] Read colors/cell-size/window-size from config or constants (no magic numbers in logic).
T-0262 [P6][orch] Emit structured per-turn CLI logs: turn#, role, NL message, tool call, resulting position, server URL.
T-0263 [P6][orch] Route CLI logs through logging_setup so they are the graded cloud-MCP comms evidence.
T-0264 [P6][sdk] Wire SDK.run_local_game(gui=True) to drive the viewer alongside the engine.
T-0265 [P6][cli] Add a --gui flag to the run subcommand.
T-0266 [P6][test] Test render functions build the expected draw calls for a fixture GameState (mock pygame).
T-0267 [P6][test] Test the viewer no-ops cleanly when no display is available.
T-0268 [P6][test] Test the log formatter includes the MCP URL and the NL message.
T-0269 [P6][test] Test the screenshot path resolves under assets/.
T-0270 [P6][test] Set SDL_VIDEODRIVER=dummy in GUI tests (rule 6/17).
T-0271 [P6][qa] Capture a GUI screenshot manually and store under assets/ (live).
T-0272 [P6][qa] Confirm coverage gate, ruff, and line cap on Phase 6 files.
T-0273 [P6][docs] Save docs/prompts/006_phase6_gui.md prompt log.
T-0274 [P6][git] Commit per GUI module and push; confirm CI green.

## Phase 7 — Full autonomous local run (6 sub-games, sanity ladder)

T-0275 [P7][orch] Create orchestrator/runner.py running a full GAME (num_games sub-games) against local MCP servers (E5).
T-0276 [P7][orch] Implement Technical-Loss handling in the runner: void + rerun until 6 VALID sub-games complete (E13).
T-0277 [P7][orch] Accumulate cop/thief totals across the 6 valid sub-games.
T-0278 [P7][orch] Assemble the internal-game JSON (schema §9.1) from final GameState + totals.
T-0279 [P7][orch] Populate group_name, students, github_repo from config.
T-0280 [P7][orch] Populate cop_mcp_url, thief_mcp_url, timezone from config.
T-0281 [P7][orch] Populate sub_games[] with per-sub-game results and totals{cop,thief}.
T-0282 [P7][orch] Keep runner.py <=150 lines.
T-0283 [P7][orch] Ensure the run is fully autonomous from init to (saved) report with zero manual steps (E5).
T-0284 [P7][orch] Run the sanity ladder 2x2 via config override and save a transcript to reports/.
T-0285 [P7][orch] Run the sanity ladder 3x3 via config override and save a transcript to reports/.
T-0286 [P7][orch] Run the sanity ladder 4x4 via config override and save a transcript to reports/.
T-0287 [P7][orch] Run the sanity ladder 5x5 (default) and save a transcript to reports/.
T-0288 [P7][sdk] Wire SDK.run_full_game() to return the report dict + transcript and save reports/internal_game.json.
T-0289 [P7][cli] Add cosmos77-pursuit run --local --games 6 full-game invocation.
T-0290 [P7][test] Test a full game produces exactly 6 valid sub-games (mocked agents).
T-0291 [P7][test] Test a Technical-Loss triggers a rerun and still yields 6 valid sub-games.
T-0292 [P7][test] Test the internal-game JSON validates against the §9.1 schema.
T-0293 [P7][test] Test the accumulated totals are correct across sub-games.
T-0294 [P7][test] Test the runner reads grid overrides from config for the sanity ladder.
T-0295 [P7][test] Test the saved internal_game.json round-trips through json.load.
T-0296 [P7][test] Mock all agents/Gemini/MCP in the runner tests (rule 6).
T-0297 [P7][qa] Live: run a full 6-sub-game autonomous game and confirm reports/internal_game.json has 6 sub_games + totals.
T-0298 [P7][qa] Confirm coverage gate, ruff, and line cap on Phase 7 files.
T-0299 [P7][docs] Commit a sample reports/internal_game.json artifact.
T-0300 [P7][docs] Save docs/prompts/007_phase7_runner.md prompt log.
T-0301 [P7][git] Commit per runner change and push; confirm CI green.

## Phase 8 — Cloud deployment (public MCP URLs + token auth)

T-0302 [P8][deploy] Create deploy/tunnel.sh exposing localhost:8001 and :8002 via cloudflared (two public HTTPS URLs) (E6).
T-0303 [P8][deploy] Document that free-tunnel URLs change on restart and must be written back to config.yaml.
T-0304 [P8][deploy] Create deploy/horizon.md step-by-step Prefect Horizon deploy (hosted FastMCP Cloud option).
T-0305 [P8][deploy] In horizon.md note the spec is platform-agnostic ("Prefect Cloud or a similar platform" + tunnels).
T-0306 [P8][deploy] Document creating TWO Horizon services with entrypoints cop_server:mcp and thief_server:mcp.
T-0307 [P8][deploy] Document setting token env vars as Horizon secrets and obtaining the two *.fastmcp.app/mcp URLs.
T-0308 [P8][deploy] Document the public-reachability/firewall requirement (MCP URLs must not sit behind a firewall).
T-0309 [P8][config] Allow config.yaml mcp.cop_url/thief_url to point at cloud URLs (via config, not hardcode).
T-0310 [P8][cli] Add a --cloud flag so the orchestrator targets the cloud servers with the orchestrator token.
T-0311 [P8][orch] Ensure the orchestrator reads cloud URLs from config and attaches the orchestrator token.
T-0312 [P8][deploy] Document token revocation: rotating COP_MCP_TOKEN/THIEF_MCP_TOKEN immediately revokes access.
T-0313 [P8][qa] Live: run a short game against the CLOUD URLs to prove the pipeline works over the public internet (E6).
T-0314 [P8][qa] Capture the cloud-run CLI logs as graded evidence and store under assets/.
T-0315 [P8][test] Test the orchestrator reads cloud URLs from config and attaches the token (mock the client).
T-0316 [P8][test] Test --cloud selects cloud URLs while --local selects localhost URLs.
T-0317 [P8][test] No real network in CI for the deploy tests (rule 6).
T-0318 [P8][deploy] Add a helper to update config.yaml mcp URLs after a tunnel restart.
T-0319 [P8][deploy] Document the LLM stays local; only the two MCP servers go public.
T-0320 [P8][qa] Confirm coverage gate, ruff, and line cap on Phase 8 files.
T-0321 [P8][docs] Commit deploy/ docs and the cloud-run CLI log capture in assets/.
T-0322 [P8][docs] Save docs/prompts/008_phase8_deploy.md prompt log.
T-0323 [P8][git] Commit per deploy artifact and push; confirm CI green.

## Phase 9 — Automated Gmail JSON report

T-0324 [P9][report] Create report/builder.py building the internal-game JSON from final GameState/totals (schema §9.1) (E7).
T-0325 [P9][report] Implement a CANONICAL serializer (sorted keys, fixed formatting) for byte-identical reports.
T-0326 [P9][report] Keep builder.py <=120 lines.
T-0327 [P9][report] Create report/schema.py pydantic models for the internal-game JSON.
T-0328 [P9][report] Add pydantic models for the bonus_game JSON (schema §9.2) in schema.py.
T-0329 [P9][report] Validate the report against the schema before sending.
T-0330 [P9][report] Create report/gmail_sender.py using the Gmail API with scope gmail.send.
T-0331 [P9][report] Implement credentials.json -> token.json via InstalledAppFlow.run_local_server with auto-refresh.
T-0332 [P9][report] Build a MIME message whose BODY IS THE RAW JSON (no prose).
T-0333 [P9][report] Base64url-encode the MIME message and call service.users().messages().send(userId="me", body={"raw": raw}).
T-0334 [P9][report] Set To = config report.to (rmisegal+uoh26b@gmail.com).
T-0335 [P9][report] Keep gmail_sender.py <=120 lines and lazy-import googleapiclient (pragma no cover).
T-0336 [P9][report] Ensure credentials.json/token.json are gitignored and never committed (rule 9).
T-0337 [P9][orch] Trigger report build + send automatically from the COP agent at the end of 6 valid sub-games (autonomous, E5/E7).
T-0338 [P9][cli] Add a cosmos77-pursuit report --send subcommand.
T-0339 [P9][test] Test the builder emits schema-valid internal-game JSON.
T-0340 [P9][test] Test the email body is JSON-only (no extra prose text).
T-0341 [P9][test] Test the sender base64url-encodes and calls messages().send with userId="me" (mock googleapiclient).
T-0342 [P9][test] Test the token-refresh path is covered.
T-0343 [P9][test] Test the canonical serializer produces identical bytes for identical input (determinism).
T-0344 [P9][test] Test schema validation rejects a malformed report.
T-0345 [P9][test] Mock all Gmail I/O; no real email in the suite (rule 6).
T-0346 [P9][qa] Live: run report --send once (Google consent first run; writes token.json; sends JSON to rmisegal+uoh26b@gmail.com).
T-0347 [P9][qa] Confirm coverage gate, ruff, and line cap on Phase 9 files.
T-0348 [P9][docs] Commit reports/ sample artifacts.
T-0349 [P9][docs] Save docs/prompts/009_phase9_report.md prompt log.
T-0350 [P9][git] Commit per report module and push; confirm CI green.

## Phase 10 — Scientific Dec-POMDP README

T-0351 [P10][readme] Write the README title: COSMOS77-ex06 — Cops & Robbers: Dual AI Agents over MCP (203.3763 HW6).
T-0352 [P10][readme] Add authors (Abdallah Khaldi 212389712 / עבדאללה חאלדי; Tasneem Natour 323118794 / תסנים נאטור), course, date.
T-0353 [P10][readme] Write the formal Dec-POMDP model section with the tuple <n, S, {Ai}, P, R, {Omega_i}, O, gamma>.
T-0354 [P10][readme] Define n=2 and the state space S = positions + barriers explicitly (E11).
T-0355 [P10][readme] Define action sets {Ai} = moves + barrier (cop) explicitly.
T-0356 [P10][readme] Define the transition function P for the grid dynamics.
T-0357 [P10][readme] Define the reward R from the scoring table.
T-0358 [P10][readme] Define the observation sets {Omega_i} and observation function O as partial/local views.
T-0359 [P10][readme] Define the discount factor gamma and its role.
T-0360 [P10][readme] Write the system architecture section: MCP Server/Client separation (LLM in orchestrator, tools in servers) (E3).
T-0361 [P10][readme] Describe the two FastMCP servers and the Gemini native-MCP tool-calling loop.
T-0362 [P10][readme] Embed the one-turn sequence diagram from PLAN.md.
T-0363 [P10][readme] Write the orchestration-challenge analysis: managing FREE natural-language comms with no predefined protocol (E4).
T-0364 [P10][readme] Analyze linguistic ambiguity, deception/bluffing, and methods ensuring mutual understanding under partial observability.
T-0365 [P10][readme] Add example natural-language message exchanges from a real transcript.
T-0366 [P10][readme] Write the strategy section (heuristic and/or Q-Table) and embed assets/learning_curve.png if used.
T-0367 [P10][readme] Write the results section: totals across 6 sub-games + sanity-ladder (2x2->5x5) observations.
T-0368 [P10][readme] Embed GUI screenshots (assets/) showing the game in real time.
T-0369 [P10][readme] Embed CLI logs proving valid comms with the CLOUD MCP servers.
T-0370 [P10][readme] Write the deployment section (platform-agnostic; Cloudflare Tunnel default, Prefect Horizon option), token auth + revocation, firewall discussion.
T-0371 [P10][readme] Write the reproduction section: config, env, uv sync, how to run local and cloud, the automated Gmail report.
T-0372 [P10][readme] Write the bonus section (if attempted): inter-group protocol + matching-JSON mechanism.
T-0373 [P10][readme] Write the self-assessment section: score vs the 17 rules + E1–E13; recommend 85 with rationale.
T-0374 [P10][readme] Ensure README.md is >=250 lines with >=5 embedded images.
T-0375 [P10][qa] Verify grep counts: dec-pomdp / partial observability / natural language all present in README.
T-0376 [P10][qa] Verify wc -l README.md >= 250 and image count >= 5.
T-0377 [P10][docs] Save docs/prompts/010_phase10_readme.md prompt log.
T-0378 [P10][git] Commit README + assets and push; confirm CI green.

## Phase 11 — Inter-group BONUS harness (ready-to-activate)

T-0379 [P11][bonus] Create bonus/series.py orchestrating a role-swap series (E12).
T-0380 [P11][bonus] Implement first 3 sub-games: OUR cop MCP server vs THEIR thief MCP server.
T-0381 [P11][bonus] Implement last 3 sub-games: THEIR cop vs OUR thief.
T-0382 [P11][bonus] Read the four MCP URLs + tokens from a bonus config block.
T-0383 [P11][bonus] Run the cross-group game over the public cloud URLs.
T-0384 [P11][bonus] Keep series.py <=150 lines.
T-0385 [P11][bonus] Create bonus/report.py building the bonus_game JSON (schema §9.2).
T-0386 [P11][bonus] Populate report_type, groups{group_1,group_2}, both github repos.
T-0387 [P11][bonus] Populate the four MCP URLs (group_1_cop/thief, group_2_cop/thief), timezone, students.
T-0388 [P11][bonus] Populate sub_games[], totals_by_group, and bonus_claim (win 10 / lose 7 / tie 5).
T-0389 [P11][bonus] Include mutual_agreement in the bonus_game JSON.
T-0390 [P11][bonus] Reuse the SAME canonical serializer from Phase 9 so both groups emit byte-identical reports (mismatch -> 0).
T-0391 [P11][bonus] Keep report.py <=120 lines.
T-0392 [P11][bonus] Create bonus/coordinate.md partner checklist (agree config, exchange four URLs + shared token, agree who runs the engine).
T-0393 [P11][bonus] Add a diff-check script to coordinate.md comparing both groups' JSON before sending.
T-0394 [P11][test] Test series.py assigns roles correctly across the 6 sub-games.
T-0395 [P11][test] Test bonus/report builds schema-valid bonus_game JSON.
T-0396 [P11][test] Test the canonical serializer is deterministic (same input -> identical bytes).
T-0397 [P11][test] Test bonus_claim computed correctly for win/lose/tie.
T-0398 [P11][test] Test totals_by_group aggregation across the role-swapped sub-games.
T-0399 [P11][test] Mock all network/agents in bonus tests (rule 6).
T-0400 [P11][qa] Confirm coverage gate, ruff, and line cap on Phase 11 files.
T-0401 [P11][docs] Commit reports/bonus_game.sample.json artifact.
T-0402 [P11][docs] Save docs/prompts/011_phase11_bonus.md prompt log.
T-0403 [P11][git] Commit per bonus module and push; confirm CI green.

## Phase 12 — Final QA gauntlet + acceptance audit

T-0404 [P12][qa] Run ruff check . and confirm zero violations.
T-0405 [P12][qa] Run ruff format --check and confirm clean.
T-0406 [P12][qa] Run check_line_cap and confirm zero offenders.
T-0407 [P12][qa] Run pytest --cov-fail-under=85 and confirm green (no live Gemini/MCP/Gmail/GUI).
T-0408 [P12][qa] Write docs/ACCEPTANCE.md mapping E1 -> file/test/artifact -> status.
T-0409 [P12][qa] Map E2 (two FastMCP servers + token auth) in ACCEPTANCE.md.
T-0410 [P12][qa] Map E3 (Server/Client separation) in ACCEPTANCE.md.
T-0411 [P12][qa] Map E4 (free natural language + partial obs) in ACCEPTANCE.md.
T-0412 [P12][qa] Map E5 (fully autonomous pipeline) in ACCEPTANCE.md.
T-0413 [P12][qa] Map E6 (local -> cloud public URLs) in ACCEPTANCE.md.
T-0414 [P12][qa] Map E7 (automated Gmail JSON report) in ACCEPTANCE.md.
T-0415 [P12][qa] Map E8 (config file, no hardcoding) in ACCEPTANCE.md.
T-0416 [P12][qa] Map E9 (decision mechanism) in ACCEPTANCE.md.
T-0417 [P12][qa] Map E10 (GUI + CLI logs) in ACCEPTANCE.md.
T-0418 [P12][qa] Map E11 (scientific Dec-POMDP README) in ACCEPTANCE.md.
T-0419 [P12][qa] Map E12 (inter-group bonus ready) in ACCEPTANCE.md.
T-0420 [P12][qa] Map E13 (Technical-Loss handling) in ACCEPTANCE.md.
T-0421 [P12][qa] Autonomy proof: a single command runs init -> 6 valid sub-games (cloud MCP) -> automated Gmail JSON with zero manual steps.
T-0422 [P12][qa] Confirm Technical-Loss reruns work end-to-end.
T-0423 [P12][qa] Server/Client separation check: assert + document the LLM is never imported/called inside mcp_servers/.
T-0424 [P12][qa] Free-language check: confirm the transcript shows genuine NL messages (not numeric) + at least one partial-observation inference moment.
T-0425 [P12][qa] Secrets check: no .env, credentials.json, token.json, or tokens in tracked files; .env.example present.
T-0426 [P12][qa] Confirm MCP token auth is on and revocation is documented.
T-0427 [P12][qa] Run uv lock --check and confirm the lock is current.
T-0428 [P12][qa] Confirm CLAUDE.md is unchanged from Phase 0.
T-0429 [P12][qa] Confirm >=30 conventional commits referencing TODO ids, no wip/tmp messages.
T-0430 [P12][qa] Confirm GitHub Actions is green on the final commit.
T-0431 [P12][qa] Fresh-clone reproducibility: uv sync -> pytest -q in a clean checkout.
T-0432 [P12][qa] Fix any unmet acceptance criterion found during the audit.
T-0433 [P12][docs] Save docs/prompts/012_phase12_qa.md prompt log.
T-0434 [P12][git] Commit ACCEPTANCE.md + fixes and push; confirm CI green.

## Phase 13 — Cover PDF + tag + release + Moodle

T-0435 [P13][cover] Reuse scripts/generate_cover_pdf.py with exercise number = 6.
T-0436 [P13][cover] Set Group ID code COSMOS77 and self-scoring recommendation 85 in the cover fields.
T-0437 [P13][cover] Set Student 1: ID 212389712 / Abdallah / Khaldi / עבדאללה / חאלדי.
T-0438 [P13][cover] Set Student 2: ID 323118794 / Tasneem / Natour / תסנים / נאטור.
T-0439 [P13][cover] Set Link to GITHUB = https://github.com/AbdallahKhaldi/COSMOS77-ex06.
T-0440 [P13][cover] Set late submission confirmation = no.
T-0441 [P13][cover] Do NOT change template fields/layout or add text (append value runs only).
T-0442 [P13][test] Add a test asserting the cover exercise number is "6".
T-0443 [P13][test] Add a test asserting the cover GitHub URL is the ex06 repo URL.
T-0444 [P13][cover] Generate the PDF via uvx --with python-docx --with docx2pdf to ~/COSMOS77/HW6/COSMOS77-ex06.pdf.
T-0445 [P13][cover] Open the PDF and confirm filename, untouched layout, exercise = 6, ex06 URL.
T-0446 [P13][cover] Confirm *.pdf is gitignored (PDF lives at ~/COSMOS77/HW6/, not in repo).
T-0447 [P13][git] Commit the cover script/test only (not the PDF).
T-0448 [P13][git] Push, then git tag -a v1.00 -m "COSMOS77-ex06 v1.00 — HW6".
T-0449 [P13][git] Push the tag and create the GitHub release from CHANGELOG.md.
T-0450 [P13][submit] Confirm the repo is public (or add rmisegal@gmail.com as collaborator) before submission.
T-0451 [P13][submit] Confirm the automated report email reached rmisegal+uoh26b@gmail.com.
T-0452 [P13][submit] Upload COSMOS77-ex06.pdf to Moodle (both students upload separately).
T-0453 [P13][submit] For the bonus (if active): both groups email matching bonus_game JSON before the Friday 08:30 deadline.
T-0454 [P13][docs] Print the final summary + remaining manual steps.
T-0455 [P13][docs] Save docs/prompts/013_phase13_submit.md prompt log.
T-0456 [P13][git] Final commit + push; confirm CI green.

## Phase 0 — Bootstrap hardening (extended)

T-0457 [P0][scaffold] Add py.typed marker to the package for type-hint distribution (rule 16).
T-0458 [P0][scaffold] Verify all stub modules expose __all__ or docstrings (rule 15).
T-0459 [P0][shared] Add a config schema validator that fails fast on a missing required key.
T-0460 [P0][shared] Add config env-override support (env var > yaml) for ports and URLs.
T-0461 [P0][shared] Unit-test config env-override precedence.
T-0462 [P0][shared] Unit-test the gatekeeper secret-scrub on a fake AIza key.
T-0463 [P0][shared] Unit-test logging_setup produces structured records with required fields.
T-0464 [P0][ci] Add a CI job step caching the uv environment for speed.
T-0465 [P0][ci] Add a CI matrix entry pinning Python 3.11 only.
T-0466 [P0][ci] Fail CI if check_line_cap finds any file over 150 lines.
T-0467 [P0][docs] Add a docs/README pointer to the playbook authority chain.
T-0468 [P0][scaffold] Add an editorconfig for consistent whitespace.
T-0469 [P0][scaffold] Add a Makefile or task aliases for sync/lint/test/run (optional convenience).
T-0470 [P0][qa] Verify uv run cosmos77-pursuit --help shows the registered subcommands.
T-0471 [P0][test] Test the CLI entry point imports without side effects.
T-0472 [P0][scaffold] Confirm reports/ and assets/ have .gitkeep so empty dirs survive clone.

## Phase 2 — Game logic hardening (extended)

T-0473 [P2][game] Add a deterministic start-position generator (seeded) honoring grid bounds.
T-0474 [P2][game] Add a guard preventing barrier placement on a cell occupied by either agent.
T-0475 [P2][game] Add a guard preventing barrier placement on the thief's current cell.
T-0476 [P2][game] Add per-sub-game barrier counter reset between sub-games.
T-0477 [P2][game] Add a move-counter that increments per full turn (thief + cop) correctly.
T-0478 [P2][game] Add an explicit SubGameResult dataclass (winner, moves_used, reason).
T-0479 [P2][game] Add a GameResult dataclass (per-sub-game results + totals).
T-0480 [P2][test] Test the start-position generator never collides cop and thief.
T-0481 [P2][test] Test barrier placement is rejected on occupied cells.
T-0482 [P2][test] Test the barrier counter resets between sub-games.
T-0483 [P2][test] Test the move counter increments once per full thief+cop turn.
T-0484 [P2][test] Test SubGameResult records the correct reason (capture vs survival).
T-0485 [P2][test] Test GameResult totals equal the sum of per-sub-game scores.
T-0486 [P2][test] Property-test that capture is symmetric in coordinate ordering.
T-0487 [P2][game] Add a Chebyshev-distance helper used when diagonal moves are allowed.
T-0488 [P2][test] Test Chebyshev distance is used for adjacency when diagonal is enabled.
T-0489 [P2][game] Add a board-to-ascii renderer for CLI debugging.
T-0490 [P2][test] Test the ascii renderer marks cop/thief/barrier cells.

## Phase 3 — MCP server hardening (extended)

T-0491 [P3][mcp] Add a vision-radius config knob controlling the partial-observation window.
T-0492 [P3][mcp] Implement get_local_observation to honor the vision radius from config.
T-0493 [P3][test] Test the observation window size follows the configured vision radius.
T-0494 [P3][mcp] Add a tool returning legal moves for the caller's own position only.
T-0495 [P3][test] Test the legal-moves tool excludes blocked/out-of-bounds cells.
T-0496 [P3][mcp] Add a server health/readiness endpoint for deploy probes.
T-0497 [P3][test] Test the health endpoint returns ok without auth (read-only liveness).
T-0498 [P3][mcp] Ensure each tool has a docstring describing its partial-observation contract (rule 15).
T-0499 [P3][mcp] Add type hints to every tool signature (rule 16).
T-0500 [P3][test] Test a tool call mutating state requires a valid token.
T-0501 [P3][test] Test concurrent in-memory clients do not corrupt shared GameState.
T-0502 [P3][mcp] Document the exact scopes each role's token carries.
T-0503 [P3][test] Test scope enforcement rejects a token lacking the read scope.
T-0504 [P3][mcp] Add structured logging of tool invocations (tool name, role, result) without leaking ground truth.
T-0505 [P3][test] Test tool-invocation logs do not contain the opponent's exact position.

## Phase 4 — Orchestrator hardening (extended)

T-0506 [P4][orch] Add a retry/backoff wrapper for Gemini rate-limit (429) responses.
T-0507 [P4][test] Test the retry wrapper backs off and retries on a mocked 429.
T-0508 [P4][orch] Add a per-turn timeout so a stalled LLM call cannot hang the game.
T-0509 [P4][test] Test a timed-out turn is recorded as a Technical-Loss candidate.
T-0510 [P4][orch] Add a fallback to the heuristic action when the LLM returns no valid tool call.
T-0511 [P4][test] Test the heuristic fallback fires when the mocked LLM returns no action.
T-0512 [P4][orch] Validate every LLM-chosen move against legal_moves before applying it.
T-0513 [P4][test] Test an illegal LLM move is rejected and re-prompted/fallen-back.
T-0514 [P4][orch] Persist the full transcript to results/ per sub-game for later analysis.
T-0515 [P4][test] Test the transcript file is written with one entry per turn.
T-0516 [P4][orch] Add a position-estimate tracker per agent updated from received NL messages.
T-0517 [P4][test] Test the estimate tracker updates from a mocked NL message implying a location.
T-0518 [P4][orch] Ensure the prompt forbids leaking ground-truth coordinates the agent should not know.
T-0519 [P4][test] Test the prompt never embeds the opponent's exact ground-truth cell.
T-0520 [P4][orch] Add a deception-allowed flag (config) controlling whether bluffing is encouraged.
T-0521 [P4][test] Test the deception flag toggles the prompt framing.
T-0522 [P4][orch] Add a turn-summary logger emitting the graded structured line per turn.

## Phase 5 — Strategy hardening (extended)

T-0523 [P5][strategy] Add config-driven alpha/gamma/epsilon hyper-parameters for the Q-Table.
T-0524 [P5][test] Test the Q-Table reads hyper-parameters from config.
T-0525 [P5][strategy] Add epsilon decay over episodes for the learning curve.
T-0526 [P5][test] Test epsilon decays monotonically across episodes.
T-0527 [P5][strategy] Add Q-Table persistence to results/ (save/load).
T-0528 [P5][test] Test the Q-Table round-trips through save/load.
T-0529 [P5][strategy] Add a state-encoding helper mapping positions to a hashable key.
T-0530 [P5][test] Test the state encoding is stable and collision-free for distinct states.
T-0531 [P5][strategy] Add a tie-break rule for equal-distance heuristic moves (deterministic).
T-0532 [P5][test] Test the heuristic tie-break is deterministic under a fixed seed.
T-0533 [P5][strategy] Add an escape-cut heuristic scoring barriers by escape-route reduction.
T-0534 [P5][test] Test the escape-cut heuristic prefers the barrier that removes the most escape cells.
T-0535 [P5][strategy] Plot reward moving-average alongside raw reward in the learning curve.
T-0536 [P5][test] Test the moving-average computation on a known reward sequence.
T-0537 [P5][docs] Document hyper-parameter choices and their effect in PRD_strategy.md.
T-0538 [P5][strategy] Add a no-op strategy mode so the LLM can decide entirely on its own.

## Phase 6 — GUI hardening (extended)

T-0539 [P6][gui] Add a message panel rendering both agents' latest NL messages with role labels.
T-0540 [P6][test] Test the message panel truncates long messages without crashing.
T-0541 [P6][gui] Add a move-counter and sub-game indicator to the HUD.
T-0542 [P6][test] Test the HUD shows the current move number and sub-game index.
T-0543 [P6][gui] Add a barrier sprite distinct from agent sprites.
T-0544 [P6][test] Test barrier cells render with the barrier sprite in draw calls.
T-0545 [P6][gui] Add an auto-screenshot-on-capture so the decisive frame is saved.
T-0546 [P6][test] Test the auto-screenshot fires on a capture event (mock pygame).
T-0547 [P6][gui] Add a configurable frame delay so runs are watchable.
T-0548 [P6][test] Test the frame delay reads from config.
T-0549 [P6][gui] Ensure the viewer closes cleanly on window-close without leaking the game loop.
T-0550 [P6][test] Test the viewer teardown is called on exit.
T-0551 [P6][gui] Add a legend explaining colors/sprites for README screenshots.
T-0552 [P6][test] Test the legend draw calls are produced for a fixture state.

## Phase 7 — Runner hardening (extended)

T-0553 [P7][orch] Add a max-rerun cap for Technical-Loss to avoid infinite reruns.
T-0554 [P7][test] Test the rerun cap aborts gracefully after N consecutive technical losses.
T-0555 [P7][orch] Tag each sub-game in the report as valid or voided with a reason.
T-0556 [P7][test] Test voided sub-games carry a reason field and are excluded from totals.
T-0557 [P7][orch] Compute and store min/max game-score bounds (30/90) for sanity checks.
T-0558 [P7][test] Test the final game score falls within the configured min/max bounds.
T-0559 [P7][orch] Save a human-readable run summary alongside the JSON report.
T-0560 [P7][test] Test the run summary lists all 6 valid sub-game outcomes.
T-0561 [P7][orch] Add a deterministic seed flag so a run is reproducible for debugging.
T-0562 [P7][test] Test the same seed yields the same mocked-run outcome.
T-0563 [P7][orch] Time each sub-game and record durations for the report metadata.
T-0564 [P7][test] Test sub-game durations are recorded as non-negative numbers.
T-0565 [P7][orch] Add a dry-run mode that uses mocked agents to validate the pipeline without the LLM.
T-0566 [P7][test] Test the dry-run completes 6 sub-games without any LLM call.
T-0567 [P7][docs] Document the sanity-ladder observations in PRD_game.md for the README.
T-0568 [P7][orch] Ensure the runner is idempotent: rerunning overwrites the report cleanly.

## Phase 8 — Deploy hardening (extended)

T-0569 [P8][deploy] Add a preflight check that both cloud MCP URLs respond before a run.
T-0570 [P8][test] Test the preflight reports which URL is unreachable (mocked client).
T-0571 [P8][deploy] Add a config profile (local vs cloud) selected by a single flag.
T-0572 [P8][test] Test the profile selector returns the correct URL set.
T-0573 [P8][deploy] Document HTTPS/TLS expectations for the public MCP endpoints.
T-0574 [P8][deploy] Add a token-rotation runbook to deploy/ docs.
T-0575 [P8][test] Test the orchestrator picks up a rotated token from env on restart.
T-0576 [P8][deploy] Add a cloudflared start/stop helper logging the generated public URLs.
T-0577 [P8][test] Test the URL-writeback helper updates config.yaml deterministically.
T-0578 [P8][deploy] Document the Prefect Horizon GitHub-push -> *.fastmcp.app/mcp flow with screenshots placeholders.
T-0579 [P8][deploy] Document the firewall/NAT failure mode and how tunnels resolve it.
T-0580 [P8][qa] Capture a second cloud-run transcript at default grid for the README evidence (live).
T-0581 [P8][test] Test that no localhost URL leaks into a cloud-profile run.
T-0582 [P8][deploy] Add a smoke script that lists tools on each cloud URL with the orchestrator token (live).
T-0583 [P8][qa] Confirm the cloud run produces a valid internal_game.json identical in shape to local.

## Phase 9 — Report hardening (extended)

T-0584 [P9][report] Add an ISO-8601 timestamp (configured timezone) to the report metadata.
T-0585 [P9][test] Test the timestamp uses the configured Asia/Jerusalem timezone.
T-0586 [P9][report] Add a schema version field to the internal-game JSON.
T-0587 [P9][test] Test the schema version field is present and validated.
T-0588 [P9][report] Add a guard refusing to send if schema validation fails.
T-0589 [P9][test] Test the sender is not called when validation fails.
T-0590 [P9][report] Add a dry-run report mode that writes the JSON without sending the email.
T-0591 [P9][test] Test the dry-run writes the JSON and never calls Gmail.
T-0592 [P9][report] Log the Gmail message id on a successful send (without leaking the token).
T-0593 [P9][test] Test the success log records a message id from a mocked send.
T-0594 [P9][report] Handle a token-refresh failure by re-running the consent flow path.
T-0595 [P9][test] Test the consent-flow path is invoked on an expired/invalid token (mocked).
T-0596 [P9][report] Ensure the JSON body has no trailing prose or signature (JSON-only, E7).
T-0597 [P9][test] Test the raw MIME body parses cleanly as JSON.
T-0598 [P9][report] Document the OAuth desktop-client setup and Test-user requirement in PRD_report.md.
T-0599 [P9][report] Add a sample reports/internal_game.sample.json committed as a reference artifact.

## Phase 10 — README hardening (extended)

T-0600 [P10][readme] Add a table of contents to the README.
T-0601 [P10][readme] Add an architecture diagram image to assets/ and embed it.
T-0602 [P10][readme] Add a partial-observability worked example (what each agent sees vs ground truth).
T-0603 [P10][readme] Add a transcript excerpt showing a successful deception/bluff and the opponent's inference.
T-0604 [P10][readme] Add a results table of per-sub-game outcomes and cumulative totals.
T-0605 [P10][readme] Add a deployment-evidence section with the cloud CLI log screenshot.
T-0606 [P10][readme] Add a limitations/future-work section (free-tier variability, cloud cold-starts).
T-0607 [P10][readme] Cross-reference each acceptance criterion E1–E13 to its README section.
T-0608 [P10][readme] Add a quick-start command block for local and cloud runs.
T-0609 [P10][qa] Verify every embedded image path resolves to a file in assets/.
T-0610 [P10][qa] Verify the README renders without broken Markdown links.
T-0611 [P10][readme] Add the Dec-POMDP tuple as a formatted block for readability.
T-0612 [P10][readme] Add a glossary of the spec vocabulary used in the README.

## Phase 11 — Bonus hardening (extended)

T-0613 [P11][bonus] Add a bonus config block schema (four URLs, shared token, partner metadata).
T-0614 [P11][test] Test the bonus config schema rejects a missing URL.
T-0615 [P11][bonus] Add a both-sides-run-and-compare mode producing two reports to diff.
T-0616 [P11][test] Test the compare mode flags any byte difference between the two reports.
T-0617 [P11][bonus] Add a tie-handling path computing bonus_claim = 5 on equal totals.
T-0618 [P11][test] Test the tie path yields bonus_claim 5 for both groups.
T-0619 [P11][bonus] Ensure mutual_agreement is only set true when both reports match byte-for-byte.
T-0620 [P11][test] Test mutual_agreement stays false on a mismatch.
T-0621 [P11][bonus] Document the partner-recruitment checklist and deadline in coordinate.md.
T-0622 [P11][test] Test role assignment swaps exactly at the midpoint (after 3 sub-games).
T-0623 [P11][bonus] Add a canonical-serializer conformance test shared with Phase 9.
T-0624 [P11][bonus] Add a sample two-group bonus_game JSON pair under reports/ for documentation.

## Phase 12 — Final audit hardening (extended)

T-0625 [P12][qa] Grep the codebase to confirm no hardcoded grid/scoring/ports/URLs/model (E8).
T-0626 [P12][qa] Grep mcp_servers/ to confirm zero LLM/Gemini imports (E3 enforced).
T-0627 [P12][qa] Confirm the transcript contains at least one non-trivial NL message per turn (E4).
T-0628 [P12][qa] Confirm every public function has a docstring (rule 15).
T-0629 [P12][qa] Confirm every public signature has type hints (rule 16).
T-0630 [P12][qa] Confirm all tests are deterministic (seeded, mocked I/O) with no flakes (rule 17).
T-0631 [P12][qa] Confirm both authors appear in the commit history.
T-0632 [P12][qa] Confirm the version remains 1.00 across pyproject, version.py, and config.yaml.
T-0633 [P12][qa] Run the full pipeline once more end-to-end against cloud URLs as the final autonomy proof.
T-0634 [P12][qa] Confirm the automated Gmail report send succeeds in the final proof run (live).
T-0635 [P12][qa] Update docs/ACCEPTANCE.md statuses to PASS for every met criterion.
T-0636 [P12][qa] File a follow-up note for any criterion not fully met and its remediation.

## Phase 13 — Submission hardening (extended)

T-0637 [P13][submit] Verify the GitHub repo visibility allows the lecturer to access the code.
T-0638 [P13][submit] Verify the release v1.00 is published with notes from CHANGELOG.md.
T-0639 [P13][submit] Verify COSMOS77-ex06.pdf exists at ~/COSMOS77/HW6/ and is not tracked in the repo.
T-0640 [P13][submit] Re-open the cover PDF to confirm Hebrew/English names render correctly.
T-0641 [P13][submit] Confirm the self-score 85 appears on the cover and in the README self-assessment.
T-0642 [P13][submit] Prepare the final submission checklist for both students' Moodle uploads.
T-0643 [P13][submit] Confirm the bonus deadline and the matching-JSON procedure with the partner group (if active).
T-0644 [P13][submit] Archive the final transcripts and screenshots referenced by the README.
T-0645 [P13][submit] Print a one-page submission summary with all artifact locations.
T-0646 [P13][git] Final verification: fresh clone, uv sync, pytest -q green, CI green on main.
