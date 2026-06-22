# Phase 8 — Cloud deployment + the cloud STATE-SYNC fix (E6)

## Goal
Promote the two FastMCP servers from local-only to **public HTTPS** and add a `--cloud`
flag so the orchestrator drives a full game over the internet with revocable token auth.
The headline is the **cloud state-sync fix** (the gap deferred from Phase 4): when the
cop and thief servers run as **separate processes**, each builds its own `GameState` via
`make_state()`, so their boards DIVERGE. The orchestrator (client) must own the
authoritative state and mirror the canonical board to BOTH servers after every turn,
while each server STILL redacts to a partial view in `get_local_observation` (E4 holds).

## The state-sync design
- **Authority:** the engine owns the one authoritative `GameState`. Local runs share it
  in-process via `_StateProxy` (Phase 4, unchanged). Cloud runs cannot share Python
  memory across processes, so a sync layer mirrors it.
- **New orchestrator-only MCP tools** (`mcp_servers/server.py`, backed by
  `mcp_servers/state_mirror.py` to keep `tools.py` ≤150):
  - `sync_state(state)` — overwrites the server's `GameState` IN PLACE from the
    orchestrator's canonical board (the server keeps its handle).
  - `get_full_state()` — returns the server's full ground truth.
  Both are gated by `_assert_orchestrator()`: the bearer token must carry BOTH `cop` and
  `thief` scopes (only the orchestrator token does; a single-role token is rejected).
  Outside HTTP (in-memory transport) the gate is a no-op, matching `_assert_scope`.
- **Per-turn reconcile** (`orchestrator/sync.py` + a `getattr`-guarded hook in
  `turn.py` / `engine.play_sub_game`, so `engine.py` stays at the 150-line cap):
  `ClientStateSync.reconcile(engine_state, acted_role)` PULLS the acting server's
  `get_full_state` (it just applied the move), copies it onto the engine's authoritative
  state, then PUSHES it to BOTH servers via `sync_state`. At each sub-game reset
  `push(state)` mirrors the fresh board. The local builder attaches no `state_sync`, so
  the reconcile is a pure no-op there and Phase-4 behaviour is byte-identical.
- **E4 stays intact:** `sync_state` sets internal TRUTH only; the LLM never sees its
  output. The LLM-facing `get_local_observation` still redacts the opponent (no global
  `thief_pos`/`cop_pos` field), as the tests assert directly.
- **No game-logic duplication:** the engine never re-implements movement/capture for the
  cloud path; it adopts the acting server's computed truth and mirrors it.

## --cloud flag
- `orchestrator/cloud.py` (≤150) mirrors `local.py`'s structure but opens an authenticated
  `Client(url, auth=BearerAuth(ORCHESTRATOR_TOKEN))` per server against the CONFIG URLs
  (`mcp.cop_url` / `mcp.thief_url`). It refuses any non-`https://` target and a missing
  `ORCHESTRATOR_TOKEN`. It attaches a `ClientStateSync` to the engine. Nothing is
  hardcoded — URLs from config, token from `.env` (Rule 4 / Rule 9).
- `runner.run_full_game(..., cloud=..., mcp_client_factory=...)` branches to the cloud
  builder; `SDK.run_full_game(cloud=...)` threads it through; the CLI `run --cloud`
  (already parsed) now reaches it.

## Validating consistency WITHOUT an LLM (the proof)
`tests/unit/test_deploy/`:
- **`test_state_sync.py`** — builds TWO `build_server` apps over TWO DISTINCT
  `GameState` objects (the cloud topology). `test_two_separate_states_stay_consistent_with_sync`
  moves the thief on its OWN server, runs `ClientStateSync.reconcile`, and asserts both
  servers' `get_full_state` are byte-identical AND the engine's state matches.
  `test_without_sync_two_states_diverge` is the control: with no sync the cop server's
  thief position stays stale `[0,0]` while the thief server shows `[1,1]` — the exact bug.
  `test_sync_state_updates_obs_but_still_redacts` proves E4 still holds after a sync.
- **`test_cloud_engine.py`** — drives a full short game through the cloud builder over two
  separate-state in-memory servers with a STUB gemini (fixed STAY JSON, no network),
  asserting both servers stay consistent end-to-end; plus the `runner` cloud branch.
- **`test_cloud_build.py`** — `--cloud` builds clients against the config HTTPS URLs with
  `BearerAuth(ORCHESTRATOR_TOKEN)` (FastMCP `Client` mocked, no network); rejects non-HTTPS
  and a missing token; attaches `ClientStateSync`.
- **`test_sync_auth_and_guards.py`** — `_assert_orchestrator` accepts the two-scope token,
  rejects a single-role token, no-ops without an HTTP token; and a guard that NO
  `http(s)://…/mcp` literal is hardcoded in `src/` (E8).
- Extended `test_mcp/test_servers.py` with an in-memory `sync_state` + `get_full_state`
  tool test (registration path) that re-checks redaction.

No Gemini and no real network are used in CI; a real cloud run is a manual `live` step.

## Deploy docs
- **`deploy/horizon.md`** — Prefect Horizon / FastMCP Cloud: GitHub sign-in, connect repo,
  two services (`cop_server:mcp` / `thief_server:mcp`), tokens as platform secrets, the two
  stable `https://*.fastmcp.app/mcp` URLs, config edit, `--cloud` run, revocation drill.
  Notes the spec's "Prefect Cloud" actually means Horizon and is platform-agnostic.
- **`deploy/tunnel.sh`** — the `cloudflared tunnel --url http://localhost:8001` (and 8002)
  fallback: two public HTTPS URLs, with the EPHEMERAL-URL caveat and the token-auth +
  revocation note documented inline.

## Files
- New: `orchestrator/cloud.py`, `orchestrator/sync.py`, `mcp_servers/state_mirror.py`,
  `deploy/horizon.md`, `deploy/tunnel.sh`, `tests/unit/test_deploy/*`.
- Edited: `mcp_servers/{server.py,tools.py}`, `orchestrator/{engine.py,turn.py,runner.py}`,
  `sdk/sdk.py`, `tests/unit/test_mcp/test_servers.py`, `tests/unit/test_sdk.py`.

## Gates
`uv run ruff check .` clean; `ruff format --check` clean; line-cap OK (every file ≤150);
`pytest -q -m 'not live'` = 316 passed; overall coverage ~98.7% (≥85).
