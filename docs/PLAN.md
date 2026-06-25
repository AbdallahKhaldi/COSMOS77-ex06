# PLAN.md — Architecture & Decision Plan

**Project:** COSMOS77-ex06 — Dual AI-agent Cops & Robbers over MCP servers
**Course:** Orchestration of AI Agents (203.3763), Dr. Yoram Segal (UOH), HW6
**Version:** 1.00

> **Thesis.** The graded artifact is the **orchestration**: two autonomous agents (a Cop and a Thief), each backed by its own **FastMCP server**, coordinating in **free natural language** under **partial observability**, driven by a single **orchestrator / MCP-Client** that runs **Gemini** with native MCP tool-calling. The game itself — a turn-based pursuit on a config-driven grid — is the *substrate*, not the deliverable. This document fixes the architecture (C4), the one-turn control flow (sequence diagram), the load-bearing decisions (ADR-001 … ADR-007), and the risk register. Every choice here maps back to acceptance criteria **E1–E13** (playbook §1.5).

---

## 1. Architecture overview (C4)

We describe the system at three C4 zoom levels — **Context**, **Container**, **Component**. The single hard invariant across all of them is **MCP Server/Client separation (E3)**: the **LLM lives ONLY in the orchestrator / MCP-Client**, and the two `mcp_servers/` expose **tools only** — they never import or call a model. This separation is what makes the system a genuine *distributed* multi-agent orchestration rather than a monolith.

### 1.1 Level 1 — System Context

The system is one autonomous pipeline with three external actors/systems at its boundary:

- **The operator (human, one command).** Issues a single CLI invocation (`cosmos77-pursuit run --cloud --games 6`) and then walks away. Per **E5** there is **zero manual intervention** between init and the final report. The operator's only out-of-band responsibilities are the one-time human touchpoints (API key, OAuth consent, cloud deploy), not in-loop control.
- **Google Gemini API (free tier).** The reasoning engine. The orchestrator calls `gemini-2.5-flash` via the `google-genai` SDK. Gemini receives each agent's **partial observation** plus the opponent's last **free natural-language** message, reasons about the hidden opponent position, emits its own NL message, and selects a tool action. (See ADR-001, ADR-002.)
- **Gmail API.** The terminal sink. At the end of 6 valid sub-games the **Cop agent** auto-sends **one** email whose body is **JSON only** to `rmisegal+uoh26b@gmail.com` (**E7**).

```
            ┌──────────────────────────────────────────────────────────────┐
            │                  COSMOS77-ex06 SYSTEM                          │
            │  (orchestrator drives a full Cops & Robbers game autonomously) │
            └──────────────────────────────────────────────────────────────┘
   operator                       ▲   │                         ▲
 (1 CLI cmd) ───── invokes ───────┘   │ reasons (NL + tool)     │ JSON-only
                                       ▼                         │ email (Cop)
                              ┌────────────────┐         ┌───────────────┐
                              │  Google Gemini │         │   Gmail API   │
                              │  (free tier)   │         │ (gmail.send)  │
                              └────────────────┘         └───────────────┘
```

### 1.2 Level 2 — Containers

Five deployable/runnable units. The **orchestrator** runs locally (or on a scheduler); the **two MCP servers** run locally for development and on **public HTTPS** for grading (**E6**); the **GUI** is an attached viewer; the **config** is the single source of truth (**E8**).

| Container | Tech | Responsibility | LLM inside? |
|---|---|---|---|
| **Orchestrator / MCP-Client** (`orchestrator/`, `agents/`) | Python + `google-genai` + `fastmcp` `Client` | Owns the turn loop, the two FastMCP `Client` sessions (with tokens), the `GameState`, the transcript, and the Gemini calls. The game engine. | **YES — the only place** |
| **Cop MCP Server** (`mcp_servers/cop_server.py`) | FastMCP 3.4, HTTP transport, `StaticTokenVerifier` | Exposes cop-role tools; holds no model and no illegitimate game-truth. Port 8001 / public URL. | **NO (E3)** |
| **Thief MCP Server** (`mcp_servers/thief_server.py`) | FastMCP 3.4, HTTP transport, `StaticTokenVerifier` | Exposes thief-role tools; symmetric to the cop server. Port 8002 / public URL. | **NO (E3)** |
| **GUI viewer** (`gui/`) | `pygame` | Real-time render of board, agents, barriers, and the latest NL message per agent; screenshot key → `assets/` (**E10**). Headless-safe for CI. | NO |
| **Config** (`config/config.yaml`) | YAML via `shared/config.py` | The single source of every tunable: grid, moves, games, barriers, scoring, ports, URLs, model (**E8**). | n/a |

```
                 ┌─────────────────────────────────────────────┐
   config.yaml ─▶│   ORCHESTRATOR / MCP-CLIENT  (LLM lives here)│
   (E8, single   │   engine • turn loop • GameState • transcript│◀── Gemini (E1/ADR-001)
    source of     └───────┬─────────────────────────┬───────────┘
    truth)                │ MCP (HTTP + token auth)  │ MCP (HTTP + token auth)
                          ▼                          ▼
              ┌────────────────────┐     ┌────────────────────┐
              │  COP MCP SERVER     │     │ THIEF MCP SERVER    │
              │  tools only (E3)    │     │ tools only (E3)     │
              │  :8001 / public URL │     │ :8002 / public URL  │
              └────────────────────┘     └────────────────────┘
                          ▲                          ▲
                          └────────  GUI viewer  ◀───┘ (reads GameState; E10)
```

### 1.3 Level 3 — Components (inside the orchestrator)

The orchestrator container decomposes into the components below. Each respects the **150-line cap** (ADR-007); larger units are split (e.g. `engine.py` + `turn.py`).

- **`orchestrator/engine.py` (`GameEngine`)** — owns the two FastMCP `Client`s, the `GameState`, and the per-turn loop: *thief turn → cop turn → check capture / move-limit*, up to `max_moves`, for `num_games` sub-games. Records the full transcript (every NL message + tool call + board state).
- **`orchestrator/turn.py`** — the single-turn unit extracted from the engine to honour the line cap.
- **`orchestrator/gemini_client.py`** — wraps `google-genai`: `ask(role_prompt, mcp_session) → (nl_message, tool_action)`. Every call routes through the **Gatekeeper** (token/cost meter, rule 13).
- **`agents/base.py` (`BaseAgent`) → `CopAgent` / `ThiefAgent`** — build the per-turn prompt from the agent's **partial observation** + the opponent's last NL message; instruct the LLM to (a) infer the opponent's likely position, (b) emit a free-language message (bluffing permitted), (c) choose a move/barrier tool.
- **`orchestrator/runner.py`** — drives a full game, handles **Technical-Loss** (void + rerun to reach 6 valid sub-games, **E13**), accumulates totals, assembles the internal-game JSON (schema §9.1).
- **`shared/`** — `config.py` (YAML loader), `gatekeeper.py`, `logging_setup.py`, `version.py`.
- **`game/`** — the pure, fully-tested state machine (board / moves / rules / match / state) the engine drives (**E1**, **E8**). No LLM, no MCP — deterministic.
- **`strategy/`** — heuristic core (Manhattan/Chebyshev) + **optional** tabular Q-Table (**E9**, ADR-004), consulted by the agents as a *suggested action* the LLM may accept or override.
- **`report/`** — canonical JSON builder + Gmail sender (**E7**).
- **`bonus/`** — the ready-to-activate inter-group series harness (**E12**).

---

## 2. One-turn sequence diagram

The diagram below traces **a single agent's turn** (e.g. the thief, who moves first per `turn_order`). The same flow repeats for the cop, and the pair repeats until capture or `max_moves`. The load-bearing detail: **the LLM call originates in the orchestrator**, and the **only thing crossing the network to the MCP server is a tool call** — the server never sees a prompt or a model (**E3**).

```mermaid
sequenceDiagram
    autonumber
    participant ENG as Orchestrator/Engine (MCP-Client)
    participant GK as Gatekeeper
    participant GEM as Gemini (gemini-2.5-flash)
    participant SRV as FastMCP Server (role: thief)
    participant ST as GameState (board)
    participant OPP as Opponent agent (cop, next turn)

    Note over ENG: Turn begins for the thief (thief moves first; E1)
    ENG->>SRV: get_local_observation(role="thief")  [MCP tool, token auth]
    SRV->>ST: read PARTIAL view (own cell + vision radius; NOT opponent's exact cell)
    ST-->>SRV: partial observation
    SRV-->>ENG: partial observation (partial observability; E4)
    ENG->>ENG: build prompt = partial obs + opponent's last NL message
    ENG->>GK: meter(call) — token/cost (rule 13)
    ENG->>GEM: ask(prompt, tools=[mcp_session])  [native MCP tool-calling; ADR-001]
    Note over GEM: reason about hidden opponent → free NL message + chosen tool
    GEM-->>ENG: tool_call(apply_move/place_barrier) + free natural-language message
    ENG->>SRV: apply_move(role="thief", direction)  [MCP tool, token auth]
    SRV->>ST: validate (legal move, not blocked) → update positions/barriers
    ST-->>SRV: new board state
    SRV-->>ENG: move result
    ENG->>SRV: send_message(role="thief", content=NL message)  [MCP tool]
    ENG->>ENG: append to transcript; check capture / move-limit (rules)
    ENG-->>OPP: opponent's next turn reads this NL message via receive_messages()
    Note over OPP: cop's LLM interprets the text to UPDATE its position estimate (E4)
```

**ASCII fallback (same flow):**

```
Engine --get_local_observation--> Server --read partial--> GameState
GameState --partial view--------> Server --partial obs---> Engine
Engine: build prompt (partial obs + opponent's last NL message)
Engine --(via Gatekeeper)--ask(prompt, tools=[mcp_session])--> Gemini
Gemini --tool_call + free NL message--------------------------> Engine
Engine --apply_move(role,dir)--> Server --validate+update---> GameState --new state--> Engine
Engine --send_message(role, NL)--> Server  (stored for opponent)
Engine: append transcript; check capture / move-limit
Opponent turn --receive_messages()--> reads NL --> LLM infers position estimate
```

Two invariants this diagram enforces:
1. **E3** — every Gemini arrow starts and ends at the **Engine**; no arrow from a Server to Gemini exists.
2. **E4** — the message is *free natural language* (a `content` string), not numeric coordinates; the opponent's LLM must *interpret* it, which is exactly the orchestration challenge the grade rewards.

---

## 3. Architecture Decision Records (ADR-001 … ADR-007)

> Each record is greppable as `ADR-###`. Status of all seven: **Accepted**.

### ADR-001 — FastMCP + google-genai native MCP tool-calling (no LangChain)

**Context.** We need two MCP servers and an LLM client that can call their tools. Candidate stacks: (a) FastMCP servers + `google-genai` native MCP integration; (b) a framework wrapper such as LangChain/LlamaIndex over the same servers.

**Decision.** Use **FastMCP 3.4** for both servers and the **`google-genai` SDK's native MCP tool-calling** in the client — pass the live MCP session directly: `config=genai.types.GenerateContentConfig(tools=[player_client.session], temperature=...)`. **No LangChain or other agent framework.**

**Rationale.** The spec's value is the *raw* orchestration loop — the agents talking NL over MCP — and a framework would hide exactly the boundary (Server/Client separation, the tool-call routing) that is graded. Native MCP keeps the dependency surface small (rule: "fewer deps"), keeps the loop legible for the Dec-POMDP README (E11), and lets us optionally disable automatic function calling to **log and route tool calls through the game engine** for validation. FastMCP gives us `@mcp.tool`, HTTP transport, and `StaticTokenVerifier` out of the box (E2).

**Consequences.** We own the turn loop explicitly (more code in `engine.py`, but it is the graded code). The Gemini MCP integration is officially "experimental" and exposes **tools only** — acceptable, since tools are all the servers should expose anyway (E3).

### ADR-002 — Gemini free tier for the agents' reasoning (short convos, ≈ $0)

**Context.** Each sub-game is ≤ 25 moves; a full game is 6 sub-games; the sanity ladder adds short 2×2…4×4 runs. The per-turn prompt is small (one partial observation + one short NL message).

**Decision.** Use **Google Gemini free tier**, model `gemini-2.5-flash`, `temperature: 0.2`, key from `GEMINI_API_KEY`. All cost is metered through the **Gatekeeper** (rule 13).

**Rationale.** The conversations are short and bounded, so the free tier comfortably covers development and grading at **≈ $0**. `gemini-2.5-flash` is fast and cheap, which matters because we make two LLM calls per turn (thief + cop). Low temperature keeps the agents' reasoning and message style stable enough for deterministic-ish transcripts while still allowing genuine free-language variation and the occasional bluff.

**Consequences.** Free-tier **rate limits** are the real constraint (see risk register), not cost. Mitigation: keep prompts tight, keep dev grids small, and back off/retry on 429. The choice is config-driven (`llm:` block), so swapping the model or provider later is a one-line edit (E8).

### ADR-003 — Cloud platform is **deliberately platform-agnostic**: Cloudflare Tunnel default, Prefect Horizon option

**Context.** The MCP servers must be reachable from the public internet over HTTPS with token auth (E6) — they cannot sit behind a home/corporate firewall. The spec (§6/§7) says deploy to *"Prefect Cloud **or a similar platform**"* and explicitly endorses **tunneling** (ngrok / Localtonet / Nginx reverse proxy). It is **platform-agnostic** by design.

**Decision.** Build **deploy-agnostic**. The **default** path is a **Cloudflare Tunnel** (`cloudflared`, already installed) exposing the two local FastMCP servers as two public HTTPS URLs. The **hosted option** is **Prefect Horizon** (the hosted "FastMCP Cloud", GitHub-push → `https://*.fastmcp.app/mcp`). The orchestrator targets whichever URLs `config.yaml` holds, via a `--cloud` flag.

**Rationale.** We do **not over-assert a single platform**, because the spec does not. `cloudflared` is the simplest spec-endorsed route to two public HTTPS URLs and needs no account beyond the tunnel; Horizon is the cleaner always-on hosted option for a partner-facing bonus series. Both are equally valid against E6; the URLs are pure config, so switching is free.

**Consequences.** Free Cloudflare quick-tunnel URLs **change on restart** → the runbook updates `config.yaml` each session (no hardcoding; E8). Horizon avoids that at the cost of an account + GitHub connection. Either way, token auth on the servers makes the public URLs safe and **revocable** (rotate the env tokens to revoke).

### ADR-004 — Heuristic core, **optional** Q-Table for the learning curve

**Context.** A decision mechanism is required (E9). The spec marks **RL/Q-Table as optional and recommended only** ("אופציונלי ומומלץ בלבד"). The grade is the orchestration, not the strategy.

**Decision.** Ship a **heuristic** decision core (cop: minimize Manhattan/Chebyshev distance to the *estimated* thief cell, place a barrier to cut escape when adjacent; thief: maximize distance / head for open space) operating on the agent's **estimate from the NL messages**, not ground truth. Add a **minimal tabular Q-Table** (Bellman update, ε-greedy, hyper-params from config) **only** to generate the learning-curve graph for the README.

**Rationale.** A heuristic alone fully satisfies E9 and keeps effort **proportionate** to where the grade lives. The Q-Table is cheap insurance for E11 completeness (the learning curve), not a requirement. Crucially, the strategy is a **suggested action** the LLM may accept or override — keeping the LLM (and thus the NL orchestration) in charge.

**Consequences.** If the Q-Table is skipped, the README simply omits the learning curve and notes the spec-optional status; nothing else changes. The heuristic operating on *estimates* (not truth) is what makes partial observability and NL inference matter.

### ADR-005 — Server/Client separation: the LLM lives in the client, never in the servers

**Context.** This is the single most explicitly graded architectural rule (E3, CLAUDE.md "Architecture rule"). The professor states the orchestration-over-strategy point four times.

**Decision.** The **LLM is instantiated and called only in the orchestrator / MCP-Client**. The two FastMCP servers (`mcp_servers/`) expose **tools only** — `send_message`, `receive_messages`, `get_local_observation`, `verify_position`, `apply_move`, `place_barrier` — and **never import or call** `google-genai`. `get_local_observation` returns only the **partial** view a role is allowed (own cell + a vision radius), never the opponent's exact cell.

**Rationale.** This boundary *is* the distributed multi-agent architecture: the servers are dumb, authenticated tool surfaces over the shared game truth; all reasoning, all NL generation/interpretation, and all turn control are client-side. Violating it collapses the system to a monolith and loses marks.

**Consequences.** Enforced and audited: Phase 12 asserts (and documents) that no LLM symbol is imported under `mcp_servers/`. The partial-observation tool is the mechanism that *forces* the agents to communicate and infer (E4) rather than read ground truth.

### ADR-006 — Config-driven: `config/config.yaml` is the single source of truth

**Context.** Spec §10 and rule 4 forbid hardcoding any tunable. Grid, moves, games, barriers, scoring, ports, URLs, model, report target, group metadata all vary.

**Decision.** **Everything tunable lives in `config/config.yaml`**, loaded through `shared/config.py`. No literal grid size, port, URL, score, or model name appears in code. The sanity ladder, the local→cloud switch, and the model/provider choice are all config overrides.

**Rationale.** Satisfies E8 directly; makes the system trivially re-targetable (new cloud URLs after a tunnel restart, a different model, a 3×3 sanity grid) without touching or re-testing code; keeps tests deterministic by pinning values in fixtures.

**Consequences.** A small loader and discipline tax — every new tunable must be added to the YAML and the loader, never inlined. Phase 12 audits for stray literals.

### ADR-007 — 150-line cap per file + SDK architecture

**Context.** Rules 1 and 2: a hard **150-line cap per `.py`** and an **SDK architecture** where all business logic flows through one `class SDK` that the CLI, GUI, and orchestrator call.

**Decision.** Enforce the **150-line cap** mechanically (`scripts/check_line_cap.py` in pre-commit and CI) and route all behavior through **`src/cosmos77_ex06/sdk/sdk.py`**. Oversized units are split by responsibility (e.g. `engine.py` + `turn.py`; `viewer.py` + `render.py`). Heavy deps (`pygame`, `google-genai`, `fastmcp`) are **lazily imported inside functions** so CI stays light and the suite is network/GPU/GUI-free.

**Rationale.** The cap forces single-responsibility components (which is also what makes the C4 component view clean) and keeps every file reviewable. The SDK seam gives one place to wire game logic, orchestration, strategy, and reporting, and one surface for the CLI to call — matching the "one command, fully autonomous" requirement (E5).

**Consequences.** More, smaller files and a discipline of splitting before a file grows. The lazy-import pattern means tests inject fakes rather than syncing heavy deps. Any rule that proves impossible in practice gets its own ADR appended here (per CLAUDE.md "When in doubt").

---

## 4. Risk register

| # | Risk | Likelihood / Impact | Mitigation | Maps to |
|---|---|---|---|---|
| R1 | **Cloud cold-starts** — a hosted MCP server (Horizon) or a freshly-spun tunnel is slow/unready on the first tool call, stalling the autonomous run. | Med / Med | Health-check ping each server URL before the game starts; retry with backoff on the first call; prefer a warm always-on Horizon service, or keep the `cloudflared` tunnel up for the whole run. A cold-start that voids a sub-game is handled as a **Technical-Loss** (rerun, E13). | E6, E13, ADR-003 |
| R2 | **Firewall / public reachability** — MCP URLs behind a home/corporate firewall are unreachable, so the cloud run (E6) fails. | Med / High | Never expose raw local ports; publish via **Cloudflare Tunnel** (default) or **Horizon** (option) for genuine public HTTPS (ADR-003). Verify reachability with an external `list_tools` probe before the graded run. Keep token auth on so public ≠ open. | E6, ADR-003, ADR-005 |
| R3 | **NL ambiguity / non-convergence** — free natural-language messages are misread, so an agent's position estimate drifts and the pursuit never resolves within `max_moves`. | Med / Med | Robust, role-framed prompts that ask the LLM to *restate its understanding* of the opponent's likely cell each turn; bound every sub-game at `max_moves` (the thief simply *survives* on timeout — a valid outcome, not a hang); log the inference each turn so drift is visible. Ambiguity is expected and is the orchestration *challenge*, not a bug — the README analyzes it (E11). | E4, E11, ADR-002 |
| R4 | **Gemini rate limits** — two LLM calls per turn × many turns × the sanity ladder can trip free-tier 429s mid-game. | Med / Med | Keep prompts tight and dev grids small; throttle/back-off and retry on 429; meter every call through the **Gatekeeper**; cache nothing that would break determinism. Model/provider are config-swappable if limits bite (E8). | E5, ADR-002, ADR-006 |
| R5 | **Bonus JSON mismatch** — the two groups' `bonus_game` reports differ byte-for-byte → both score **0**. | Low / High | Both groups serialize through the **same canonical serializer** (sorted keys, fixed formatting) shared from `report/output.py`; agree config + the four MCP URLs + a shared token up front; run a `diff` check on both JSONs **before** either group emails; set `mutual_agreement: true` only after the diff is clean. | E7, E12 |
| R6 | **Server/Client separation regressions** — a refactor accidentally pulls an LLM import into `mcp_servers/`, breaking E3. | Low / High | Phase-12 audit asserts no LLM symbol is importable under `mcp_servers/`; the boundary is documented in the C4 view and the sequence diagram; tools-only tool list is unit-tested. | E3, ADR-005 |
| R7 | **Gmail OAuth / scope friction** — first-run consent, scope caching, or "app not verified" blocks the automated report. | Low / Med | Use the minimal `gmail.send` scope; add self as a **Test user**; delete `token.json` when changing scopes to force fresh consent; tests mock `googleapiclient` so CI never sends mail. The real send is a one-time manual verification. | E7 |

---

## 5. Traceability — plan → acceptance criteria

| Decision / artifact | Acceptance criteria |
|---|---|
| Config-driven game machine (§1.3 `game/`, ADR-006) | E1, E8 |
| Two FastMCP servers + `StaticTokenVerifier` (§1.2, ADR-001) | E2 |
| LLM only in the orchestrator (ADR-005, sequence diagram §2) | E3 |
| Free NL messages + partial-observation inference (§2, R3) | E4 |
| One-command autonomous pipeline + Technical-Loss rerun (§1.3 `runner.py`, R1) | E5, E13 |
| Local → public HTTPS via tunnel/Horizon (ADR-003, R1/R2) | E6 |
| Canonical JSON + Cop auto-email (§1.3 `report/`, R5/R7) | E7 |
| `config/config.yaml` single source of truth (ADR-006) | E8 |
| Heuristic core + optional Q-Table (ADR-004) | E9 |
| pygame GUI + structured CLI logs (§1.2) | E10 |
| Dec-POMDP README embedding this C4 + sequence diagram | E11 |
| Ready-to-activate bonus series + shared serializer (R5) | E12 |

---

*End of PLAN.md.*
