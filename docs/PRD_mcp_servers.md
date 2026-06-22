# PRD — MCP Servers (`cop_server.py` + `thief_server.py`)

> **Module:** `src/cosmos77_ex06/mcp_servers/`
> **Acceptance criteria:** **E2** (two separate FastMCP servers, each with revocable token auth), **E3** (Server/Client separation — the LLM lives in the orchestrator, never here), **E4** (tools serve only the agent's *partial* observation, never ground truth), **E6** (local separate ports → public HTTPS cloud), **E8** (every tunable from `config/config.yaml`).
> **Phase:** 3 of the playbook (spec §13 step 2).
> **Framework:** FastMCP 3.4.x, HTTP transport, `StaticTokenVerifier` token auth.

---

## 1. Purpose and the graded boundary

This document specifies the **two FastMCP servers** that back the pursuit. The grade for HW6 is the **orchestration** — two autonomous agents coordinating in **free natural language** over **MCP** under **partial observability** — not the game strategy. The MCP servers are the *tool surface* that makes that orchestration possible, and they exist mainly to demonstrate one binding architectural property:

> **MCP Server/Client separation (E3).** The LLM (Gemini) lives **only** in the orchestrator / MCP-Client. The MCP servers expose **tools only**. No `import google.genai`, no model call, and no strategy logic ever appears under `mcp_servers/`. A reviewer must be able to grep the package and find zero LLM references in this directory.

A second, equally graded property is that the servers are the **enforcement point for partial observability (E4)**. A server never returns the full game truth. The thief's exact cell is never leaked to the cop's observation tool, and vice versa. Whatever an agent learns about its opponent must come from the opponent's **free natural-language messages** (which the agent's LLM interprets in the orchestrator), *not* from a tool that quietly reveals the opponent's coordinates. The server is therefore the **Dec-POMDP observation function `O`** made concrete: it maps the true state to a role-scoped, partial `Ωi`.

There are **two** servers, one per role, so that:
- each can be deployed and addressed independently (separate ports locally, separate HTTPS URLs in the cloud — E6),
- each carries its **own revocable token** (E2), so a single role's access can be rotated/revoked without touching the other,
- the cop-only capability (`place_barrier`) is registered **only** on the cop server, making the role asymmetry structural rather than a runtime check that could be bypassed.

---

## 2. Where the servers sit in the system

```
                 ORCHESTRATOR  (MCP Client)  ── holds the LLM (Gemini), the GameState authority,
                 the turn loop, the Gatekeeper. THIS is where reasoning happens.
                         │  native MCP tool-calling  (fastmcp.Client, bearer token)
            ┌────────────┴─────────────┐
            ▼                          ▼
   COP MCP SERVER  :8001/mcp     THIEF MCP SERVER  :8002/mcp
   tools only, NO LLM            tools only, NO LLM
   StaticTokenVerifier           StaticTokenVerifier
   place_barrier registered      place_barrier NOT registered
            └────────────┬─────────────┘
                         ▼
            shared GameState handle  (the single source of truth;
            servers read/mutate it through tool calls only)
```

The orchestrator owns the canonical `GameState` (positions, barriers, move counter, the natural-language message log). The servers operate on a **handle** to that state via the shared tool implementations. The servers never decide *what* to do — they only execute a legitimate, role-checked tool and return a legitimate, role-scoped result. The decision of *which* tool to call, and the natural-language message that accompanies it, is produced by the LLM in the orchestrator.

---

## 3. File layout (each `.py` ≤ 150 lines — Rule 1)

| File | Responsibility | Cap |
|---|---|---|
| `mcp_servers/__init__.py` | Package marker. | — |
| `mcp_servers/tools.py` | The shared, role-aware **tool implementations** operating on a `GameState` handle. No FastMCP, no LLM. Pure functions/methods so they unit-test deterministically. | ≤150 (split into `tools.py` + `observation.py` if it grows). |
| `mcp_servers/observation.py` | The partial-observation builder for `get_local_observation` (vision-radius windowing, opponent-redaction). Isolated because it is the E4 enforcement core and deserves its own tests. | ≤120 |
| `mcp_servers/auth.py` | Builds the `StaticTokenVerifier` from env tokens + required scopes. Shared by both servers (Rule 3: no duplication). | ≤60 |
| `mcp_servers/cop_server.py` | Instantiates `FastMCP("cosmos77-cop")`, registers the cop's tool set (**including** `place_barrier`), attaches auth, runs HTTP on `mcp.cop_port`. | ≤120 |
| `mcp_servers/thief_server.py` | Instantiates `FastMCP("cosmos77-thief")`, registers the thief's tool set (**no** `place_barrier`), attaches auth, runs HTTP on `mcp.thief_port`. | ≤120 |
| `mcp_servers/app.py` | Exposes `cop_app` / `thief_app` ASGI objects via `mcp.http_app()` for uvicorn / Prefect Horizon / FastMCP Cloud deployment. | ≤80 |

Because the servers must hold no game-truth beyond what a tool legitimately exposes, **all secret state lives in the `GameState` the orchestrator owns**; the server modules only carry a reference to it plus the FastMCP wiring.

---

## 4. The tool surface

Both servers expose a shared *communication + perception + action* surface; the cop server additionally exposes the cop-only `place_barrier`. Every tool is decorated with `@mcp.tool`, carries a docstring (Rule 15) and full type hints (Rule 16), validates its inputs, and returns a structured, JSON-serializable result.

> **Naming convention for `role`.** Tools accept an explicit `role: str` (`"cop"` or `"thief"`) argument as the playbook specifies, but the **server cross-checks `role` against the server's own identity and against the authenticated token's scope**. A call to the thief server with `role="cop"`, or a token without the matching role scope, is rejected. This prevents a client from impersonating the other role to coax out information it should not see.

### 4.1 `send_message(role: str, content: str) -> dict`
Append a **free natural-language** message from `role` to the shared message log (E4). `content` is opaque prose — intentions, claimed observations, bluffs, questions — never a constrained numeric protocol. Returns `{"ok": True, "turn": <int>, "message_id": <int>}`. The server does **not** parse, validate, or "understand" the message; interpretation is the receiving agent's LLM job in the orchestrator. The server is a transport + ledger only.

### 4.2 `receive_messages(role: str, since: int = 0) -> dict`
Return the natural-language messages addressed to / visible to `role` (typically the opponent's latest turn message), newest-relevant first, with their turn numbers and ids, filtered by `since` for incremental polling. Returns `{"messages": [{"id", "turn", "from", "content"}], "latest_id": <int>}`. This is the only channel through which an agent gets information about the opponent — and it is **prose the opponent chose to send**, which may be incomplete or deliberately misleading. That is the whole point of E4.

### 4.3 `get_local_observation(role: str) -> dict`  ← **the E4 enforcement tool**
Return **only** the partial, local view that `role` is permitted to see. Concretely:

```jsonc
{
  "role": "cop",
  "self": {"x": 2, "y": 1},                  // the caller's OWN exact position (always known)
  "grid_size": [5, 5],
  "vision_radius": 1,                          // from config; the Chebyshev/Manhattan window radius
  "visible_cells": [                           // cells within the vision window
    {"x": 1, "y": 0, "blocked": false, "occupant": null},
    {"x": 2, "y": 0, "blocked": true,  "occupant": null},   // a barrier is visible terrain
    {"x": 3, "y": 2, "blocked": false, "occupant": "thief"} // opponent only if INSIDE the window
  ],
  "move_number": 7,
  "moves_remaining": 18,
  "barriers_remaining": 3                      // cop only; omitted for thief
}
```

**Invariants the server guarantees (each is asserted by tests):**

1. **Own position is exact** — the caller always knows where *it* is. That is `Ωi` for the agent's own component of the state, not a leak.
2. **The opponent's exact cell is NEVER returned unconditionally.** The opponent's `(x, y)` appears in `visible_cells` **only** when that cell falls inside the caller's vision window (within `vision_radius`). Outside the window, the opponent simply does not appear — there is no "opponent position" field anywhere in the payload. This is the literal implementation of partial observability: when you can see them, you see them; otherwise you must *infer* from their natural-language messages.
3. **No global truth fields.** The payload never contains the full board occupancy map, the opponent's last move, the opponent's barrier budget, or any field that would let the caller reconstruct the hidden state. Barriers are returned as **terrain** (`blocked: true`) within the vision window only — they are placed on the board and are legitimately observable as obstacles, but the *count remaining for the opponent* is never exposed.
4. **Role-scoped redaction is computed server-side.** The orchestrator cannot ask the server for "the truth"; the redaction happens in `observation.py` before anything crosses the wire, so even a misbehaving client cannot widen its view.

`vision_radius` is read from config (`game.vision_radius`, default `1`) so the difficulty/observability of the Dec-POMDP is tunable without code changes (E8). A radius covering the whole board would make the game fully observable; the default keeps it genuinely partial.

### 4.4 `verify_position(role: str, x: int, y: int) -> dict`
A bounded **confirmation** primitive, NOT a locator. It answers a yes/no question the agent already has a hypothesis about: *"Is the cell `(x, y)` the opponent's cell?"* — and only when that cell is **inside the caller's own vision window** (otherwise it returns `{"known": false}`). It exists so an agent can corroborate an inference it formed from the opponent's prose against what it can legitimately see, without ever scanning the board for the opponent. Returns `{"known": <bool>, "result": <bool|null>}`. It can never be used to enumerate cells and triangulate the opponent, because outside the vision window it always returns `known: false`. (It may also be used to validate the caller's own intended target cell — in-bounds and not a barrier — before committing a move.)

### 4.5 `apply_move(role: str, direction: str) -> dict`
Move `role` one step in `direction` (the 8 compass directions when `allow_diagonal: true`, else the 4 orthogonals — read from config). The server validates the move against the board (in-bounds, target not a barrier) and the turn order (`turn_order: ["thief", "cop"]` — the thief moves first), mutates the shared `GameState`, increments the move counter, and runs capture detection (**capture = the cop lands on the thief's cell**). Returns `{"ok": <bool>, "new_self": {"x","y"}, "captured": <bool>, "reason": <str|null>}`. An illegal move returns `ok: false` with a reason and does **not** advance state; the orchestrator decides how to handle it (a turn wasted, a Technical-Loss, or a re-ask of the LLM). Note the result reveals `captured` and the caller's own new position — never the opponent's position.

### 4.6 `place_barrier(role: str) -> dict`  ← **cop server only**
Place a barrier that is **impassable to both** agents. Registered **only** on `cop_server.py`; it does not exist on the thief server's tool list at all (so `list_tools()` on the thief server must not contain it — a tested invariant). Enforces the cop-only rule and the `max_barriers` budget (default 5) from config. The barrier location follows the cop's strategy as decided in the orchestrator and is placed at a cell adjacent to / chosen by the cop per the tool's contract; the server only validates (in-bounds, empty, budget remaining) and mutates state. Returns `{"ok": <bool>, "cell": {"x","y"}, "barriers_remaining": <int>, "reason": <str|null>}`.

### 4.7 Tool/role matrix

| Tool | Cop server | Thief server | Notes |
|---|:--:|:--:|---|
| `send_message` | ✅ | ✅ | free NL transport |
| `receive_messages` | ✅ | ✅ | opponent's prose only |
| `get_local_observation` | ✅ | ✅ | role-scoped partial view (E4) |
| `verify_position` | ✅ | ✅ | confirm-only, window-bounded |
| `apply_move` | ✅ | ✅ | turn-order + capture enforced |
| `place_barrier` | ✅ | ❌ | cop-only; structurally absent on thief server |

---

## 5. Transport, ports, and addressing (E6, E8)

Both servers run on **HTTP transport** (streamable-HTTP MCP) so they are reachable over the network and, after deployment, over the public internet — `stdio` transport would not satisfy the public-reachability requirement.

```python
# cop_server.py (shape)
mcp.run(transport="http", host="0.0.0.0", port=config.mcp.cop_port)   # 8001 -> /mcp
# thief_server.py
mcp.run(transport="http", host="0.0.0.0", port=config.mcp.thief_port) # 8002 -> /mcp
```

Ports, base paths, and URLs are **never hardcoded** — they come from `config/config.yaml`:

```yaml
mcp:
  cop_url:   "http://localhost:8001/mcp"
  thief_url: "http://localhost:8002/mcp"
  cop_port:  8001
  thief_port: 8002
```

`host="0.0.0.0"` binds all interfaces so a tunnel (cloudflared) or a hosted runtime (Horizon / FastMCP Cloud) can forward to it. The orchestrator reads `cop_url` / `thief_url` from the same config, so switching from local to cloud is a config edit plus the `--cloud` flag — no code change (E6/E8). When a free tunnel rotates its URL on restart, only `config.yaml` is updated.

---

## 6. Token authentication (E2) — `StaticTokenVerifier`, revocable

Each server attaches a `StaticTokenVerifier` whose tokens are read **from the environment**, never from code or the repo (Rule 9). Tokens map to **required scopes**, and the role tools cross-check the scope so a token can only exercise its own role.

```python
# auth.py (shape)
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier  # FastMCP static token provider

def build_verifier(role: str) -> StaticTokenVerifier:
    """Build a static-token verifier for `role` from env tokens. No secrets in code."""
    role_token = os.environ[f"{role.upper()}_MCP_TOKEN"]          # COP_MCP_TOKEN / THIEF_MCP_TOKEN
    orch_token = os.environ["ORCHESTRATOR_TOKEN"]                  # the client's bearer token
    return StaticTokenVerifier(
        tokens={
            role_token: {"client_id": role,          "scopes": ["read", role]},
            orch_token: {"client_id": "orchestrator","scopes": ["read", "cop", "thief"]},
        },
        required_scopes=["read"],
    )
```

- The **orchestrator** authenticates with `ORCHESTRATOR_TOKEN` (a bearer token) to both servers; it is the only legitimate client.
- **Revocation is immediate and per-role:** rotating `COP_MCP_TOKEN` (locally in `.env`, or as a Horizon/FastMCP-Cloud secret) and restarting/redeploying the cop server invalidates every previously issued cop credential without affecting the thief server. This satisfies the spec's "revocable token auth" requirement (E2).
- `.env.example` ships the variable **names only**; real values are gitignored. Tests inject fake tokens, so no live secret is needed for CI (Rule 6/9).
- An unauthenticated request, or a token lacking `read` (or lacking the role scope when calling a role-scoped tool), is rejected before any tool body runs — a tested invariant.

---

## 7. The `http_app()` ASGI entrypoint (cloud deploy)

For deployment to a hosted runtime (Prefect Horizon / FastMCP Cloud) or behind uvicorn + a tunnel, each server exposes a standard **ASGI application** via FastMCP's `http_app()`:

```python
# app.py
from cosmos77_ex06.mcp_servers.cop_server import mcp as cop_mcp
from cosmos77_ex06.mcp_servers.thief_server import mcp as thief_mcp

cop_app = cop_mcp.http_app()      # ASGI app, mounted at /mcp
thief_app = thief_mcp.http_app()  # ASGI app, mounted at /mcp
```

Run locally with an ASGI server:

```bash
uvicorn cosmos77_ex06.mcp_servers.app:cop_app   --host 0.0.0.0 --port 8001
uvicorn cosmos77_ex06.mcp_servers.app:thief_app --host 0.0.0.0 --port 8002
```

**Deployment is platform-agnostic** (spec §6/§7: *"Prefect Cloud or a similar platform"*, and tunneling is explicitly endorsed). HW6 supports two paths, selected without code changes:

1. **Simple default — Cloudflare Tunnel.** Run both servers locally (uvicorn or `mcp.run`), then `cloudflared tunnel --url http://localhost:8001` (and `:8002`) to obtain two public `https://…` URLs; paste them into `config.yaml`. Installed and ready in this environment.
2. **Hosted option — Prefect Horizon / FastMCP Cloud.** Connect the repo, create two services with entrypoints `cosmos77_ex06.mcp_servers.app:cop_app` and `…:thief_app` (or the `:mcp` objects), set `COP_MCP_TOKEN` / `THIEF_MCP_TOKEN` / `ORCHESTRATOR_TOKEN` as platform secrets, and receive two `https://*.fastmcp.app/mcp` URLs.

Either way the public-reachability requirement (E6) is met — MCP URLs must not sit behind a firewall — and token auth gates them. The detailed runbook lives in `docs/PRD_deploy.md` / `deploy/`.

---

## 8. What the server must NOT do (anti-requirements)

| Forbidden | Why |
|---|---|
| Import or call an LLM (`google.genai`, etc.) inside `mcp_servers/`. | **E3** Server/Client separation. The LLM is the orchestrator's. |
| Return the opponent's exact position outside the vision window from any tool. | **E4** partial observability; the Dec-POMDP `O` is enforced here. |
| Expose a "full board" / "game truth" / "opponent state" tool. | Same — no tool may leak hidden state. |
| Hardcode ports, URLs, grid size, barrier budget, vision radius, scoring. | **Rule 4 / E8** — all from `config/config.yaml`. |
| Embed tokens or secrets in code/repo. | **Rule 9** — env only, gitignored, revocable. |
| Put strategy / decision logic in the server. | The server executes tools; the orchestrator decides. |
| Register `place_barrier` on the thief server. | Barriers are cop-only; the asymmetry is structural. |
| Let `apply_move` ignore turn order or skip capture detection. | **E1** game rules are enforced at the action boundary. |

---

## 9. Testing strategy (Phase 3, Rule 6/7/17 — no network in CI)

All MCP I/O is exercised through the **FastMCP in-memory client** so the suite needs no live network, no real tokens, and no running server. Heavy imports (`fastmcp`) are lazy and marked `# pragma: no cover`; fakes are injected.

Tested invariants (deterministic, seeded):

1. **Tool inventory per server.** `list_tools()` on the cop server contains `place_barrier`; on the thief server it does **not**. Both contain the shared five.
2. **Partial observability (the headline E4 test).** With the thief outside the cop's vision window, `get_local_observation("cop")` contains **no** field revealing the thief's cell, and `visible_cells` does not include a `"thief"` occupant. With the thief moved inside the window, it *does* appear — proving the window is the only disclosure path.
3. **`verify_position` is confirm-only.** Returns `known: false` for cells outside the vision window regardless of where the opponent actually is; cannot be used to scan.
4. **Auth.** A client with no token or a bad token is rejected; a client with `ORCHESTRATOR_TOKEN` succeeds; a token lacking the role scope cannot call a role-scoped tool.
5. **`apply_move`** updates state, honors turn order (thief first), reports `captured: true` exactly when the cop lands on the thief's cell, and rejects moves into barriers / out of bounds.
6. **`place_barrier`** decrements the budget, refuses past `max_barriers`, and the placed cell becomes impassable to a subsequent `apply_move` by *both* roles.
7. **No-LLM guard (E3).** A test (and a Phase-12 grep) asserts no LLM module is importable from `mcp_servers/`.

Coverage target ≥ 85% on the server tool logic (network mocked).

---

## 10. Acceptance-criteria traceability

| Criterion | How this module satisfies it |
|---|---|
| **E2** | Two separate FastMCP servers (`cop_server.py`, `thief_server.py`), each with a `StaticTokenVerifier` whose tokens come from env and are revocable per role. |
| **E3** | No LLM anywhere under `mcp_servers/`; the servers expose tools only; reasoning is in the orchestrator. Guarded by a test + a Phase-12 grep. |
| **E4** | `get_local_observation` / `verify_position` return only a role-scoped, vision-windowed partial view; the opponent's exact cell is never disclosed outside the window; `send_message`/`receive_messages` carry free natural-language prose, the only inter-agent information channel. |
| **E6** | HTTP transport on configurable separate ports locally → `http_app()` ASGI entrypoint for cloud (Horizon / FastMCP Cloud) or a cloudflared tunnel; URLs from config. |
| **E8** | Ports, URLs, `vision_radius`, `max_barriers`, `allow_diagonal`, `turn_order`, grid size, scoring — all read from `config/config.yaml`, nothing hardcoded. |
| **E1 (supporting)** | `apply_move` enforces turn order, bounds, barrier impassability, and capture detection; `place_barrier` enforces the cop-only ≤5 budget. The canonical rule engine lives in `game/`; the tools are its network-facing boundary. |
