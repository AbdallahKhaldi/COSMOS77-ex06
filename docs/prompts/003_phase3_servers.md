# Prompt log — Phase 3: Two FastMCP servers + token auth

**Goal.** The two MCP servers (acceptance E2, E3, E4): each exposes TOOLS ONLY (no LLM inside),
each with revocable token auth, enforcing partial observability. Playbook §5, design in
`docs/PRD_mcp_servers.md`. TDD with the FastMCP in-memory client; no network in CI.

## Approach — build → adversarial review → fix
Same three-stage workflow. The build worker first **introspected the installed FastMCP 3.4.2**
source (rather than trusting the playbook's snippets) to pin the real API, then implemented and
tested; the reviewer adversarially probed the three graded properties; the fixer hardened the
two reservations into the default CI suite.

## Verified FastMCP 3.4.2 API (from `.venv` source)
- `from fastmcp.server.auth.providers.jwt import StaticTokenVerifier` — `tokens={token: {client_id, scopes}}`, `required_scopes`, async `verify_token(token) -> AccessToken | None`.
- `FastMCP(name, auth=verifier)`; bare `@mcp.tool` decorator; `mcp.http_app()` ASGI app mounted at `/mcp`; `mcp.run(transport="http", host, port)`.
- In-memory tests: `async with Client(mcp) as c: await c.call_tool(name, args)` → `.data`. The in-memory transport bypasses HTTP bearer auth (so auth is tested at the verifier + ASGI level).

## Modules (config-driven; NO llm/genai imports — grep + `test_no_llm` verified)
`tools.py` (the six tools over a GameState handle, reusing the `game/` engine — no rule
re-implementation) · `observation.py` (the E4 redaction core: Chebyshev vision window; opponent
disclosed only when inside the window; `verify_position` is confirm-only and cannot scan) ·
`auth.py` (env-sourced `StaticTokenVerifier`, revocable per role) · `server.py` (shared
`build_server` factory; `place_barrier` registered cop-only) · `cop_server.py` / `thief_server.py`
(module-level `mcp` + `python -m ...` HTTP boot) · `state_factory.py` · `app.py` (ASGI entrypoints).

## What the review caught (all fixed for real, re-greened)
- **E2 wire-level auth (medium):** rejection was only proven by a `live`-marked test (deselected
  from CI). **Fix:** added in-process `httpx.ASGITransport` tests asserting a missing header and a
  garbage bearer both yield **401 before any tool runs** — now in the default `-m 'not live'` suite.
- **E2 role-scope cross-check (medium):** the PRD's per-tool scope gate wasn't implemented.
  **Fix:** `_assert_scope(role)` reads `get_access_token()` and rejects a token lacking the role
  scope; wired into every tool wrapper (no-op in-process, enforced over HTTP).
- **Low:** `receive_messages` now returns the *opponent's* prose only (not the caller's own echo);
  bind `host` moved to config (`mcp.host`); `vision_radius` now a strict read (fails loudly if absent).

## Verification (independently re-run)
- ruff / format / line-cap clean (all `mcp_servers/` files ≤127 lines).
- `pytest -m 'not live'` → **155 passed, 98.94%** overall; `mcp_servers/` logic ~100%.
- No `google/genai/gemini/openai/anthropic` imports anywhere under `mcp_servers/` (E3).
- Live HTTP smoke test (separate, `-m live`): correct token lists all 6 cop tools; bad token → 401.
