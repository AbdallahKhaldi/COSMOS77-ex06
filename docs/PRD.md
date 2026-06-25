# PRD — COSMOS77-ex06 (Master Product Requirements Document)

> **Project.** Dual AI-agent **Cops & Robbers** pursuit over **MCP servers**, with two
> autonomous agents (a **Cop** and a **Thief**) coordinating in **free natural language**
> under **partial observability**, driven by an **orchestrator / MCP-Client** running
> Gemini. Local first, then deployed to **public HTTPS** MCP URLs, ending with an
> **automated Gmail JSON report**.
>
> **Course.** Orchestration of AI Agents (203.3763), L09 — Dr. Yoram Segal, University of
> Haifa. **Assignment.** HW6. **Group.** `COSMOS77`. **Version.** 1.00.
>
> **The central thesis (read first).** *The grade is the **orchestration**, not the game
> strategy.* The deliverable's value is two **autonomous** agents negotiating a turn-based
> pursuit in unconstrained natural language across two independent MCP servers, fully
> autonomously from initialization through six sub-games to an automated email — with a
> clean **Server/Client separation** (the LLM lives only in the client). A "dumb" heuristic
> on a pipeline that runs end-to-end with zero human intervention against **cloud** MCP URLs
> outranks a clever strategy on a pipeline that needs nudging. Every requirement below is
> weighted accordingly.

---

## 1. Context & Motivation

### 1.1 Where this sits in the course

HW6 is the distributed-multi-agent capstone of the assignment series. HW1 was classical ML,
HW2 multi-process, HW3 PDF/document processing, HW4 reverse-engineering, HW5 benchmarking;
**HW6 is distributed multi-agent orchestration.** The course's L09 material on the
**Model Context Protocol (MCP)** and on orchestrating cooperating/competing LLM agents is
the direct subject: we must demonstrate that we can *wire two independent agents together
over a real protocol and make them act autonomously*, not merely that we can prompt one
model well.

### 1.2 The system in one paragraph

A turn-based pursuit unfolds on a config-driven grid (default 5×5). Two agents — Cop and
Thief — each own a **separate FastMCP server** that exposes *tools only* (no model inside).
A single **orchestrator** acts as the **MCP Client**: each turn it asks Gemini (native MCP
tool-calling) for an agent's next action, given that agent's **partial, local observation**
and the opponent's last **free natural-language message**; it executes the chosen tool
against that agent's MCP server, advances the board, and records the full transcript. The
agents never exchange raw coordinates as a protocol — they talk in ordinary language
(stating intentions, observations, and occasionally **deception**), and each side's LLM
**infers** the opponent's likely position from text. The game runs **six sub-games** of at
most **25 moves** each (the **thief moves first**); diagonal movement is allowed; the cop
may place up to **five barriers** that are impassable to both. Capture is the cop landing on
the thief's cell. At the end, the **Cop agent autonomously emails a JSON-only report** of
the results to the lecturer's intake address.

### 1.3 Why it is modelled as a Dec-POMDP

The pursuit is, formally, a **Decentralized Partially Observable Markov Decision Process
(Dec-POMDP)**: two decision-makers, a shared hidden state, each agent receiving only a
**local observation**, and a joint transition driven by their joint action. The scientific
README (E11) formalizes the game with the tuple **⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩**:
- **n = 2** (cop, thief);
- **S** = the joint state (both positions + the set of barrier cells + move counter);
- **{Aᵢ}** = each agent's action set (the directional moves; plus barrier placement for the
  cop);
- **P** = the deterministic transition from a joint action;
- **R** = the scoring table (below);
- **{Ωᵢ}** = each agent's observation set (its own position + a bounded local view, never
  the opponent's exact cell);
- **O** = the observation function that produces the partial view;
- **γ** = the discount factor (used only if the optional Q-Table extension is enabled).

The partial-observability tuple is not decoration: it is the formal justification for why
the **natural-language channel matters** — because neither agent can see ground truth, the
*only* way to learn about the opponent is to read and reason about the opponent's messages.
That reasoning loop is precisely the orchestration the course grades.

---

## 2. Research / Report Questions (spec §4)

The scientific write-up (E11) must answer, in high-level scientific language, the questions
the spec poses around the orchestration challenge. The PRD captures them here so every
downstream artifact can be traced back to a question:

- **RQ1 — Orchestration over strategy.** What does it take to make two independent LLM
  agents complete a full game *autonomously*, and why is that harder (and more valuable)
  than the pursuit strategy itself?
- **RQ2 — Free natural-language coordination.** How do agents coordinate with **no
  predefined numeric protocol**? How is **linguistic ambiguity** handled, and how is
  **mutual understanding** verified across turns?
- **RQ3 — Inference under partial observability.** How does each agent build and update an
  **estimate of the opponent's position** purely from natural-language messages plus its own
  local observation? What happens when a message is vague — or deliberately **deceptive**?
- **RQ4 — Server/Client separation.** Why must the LLM live in the **client/orchestrator**
  and the MCP servers expose **tools only**? What would break (correctness, security,
  gradeability) if the boundary were violated?
- **RQ5 — Public reachability & security.** What is required to make MCP servers reachable
  from the public internet behind firewalls, and how is access controlled with **revocable
  token authentication**?
- **RQ6 — The decision mechanism (E9).** Does a heuristic suffice, and what (if anything)
  does a tabular **Q-Table** add? (RL is **optional** per spec.)
- **RQ7 — Reproducibility & autonomy.** Can the whole pipeline (init → 6 valid sub-games →
  emailed report) be reproduced from a clean clone with zero manual game steps, including
  **Technical-Loss** recovery?

The README's "Orchestration-challenge analysis" section (RQ2/RQ3) is the section the grade
rewards most.

---

## 3. Functional Requirements (mapped one-by-one to E1–E13)

Each functional requirement below is stated as a testable obligation and tied to exactly one
acceptance criterion. Every parameter named is read from `config/config.yaml` — **nothing is
hardcoded** (Rule 4 / E8).

### FR-1 → E1 — Game logic (config-driven grid)
The system shall implement a grid state-machine driven entirely by config:
- a board of `grid_size` (default `[5, 5]`); the **sanity ladder** overrides this to
  2×2 → 3×3 → 4×4 → 5×5;
- **diagonal movement** when `allow_diagonal: true`;
- **barriers** placed by the **cop only**, at most `max_barriers` (5) per sub-game,
  **impassable to both** agents;
- **capture detection** = the cop lands on the thief's cell;
- **turn order** `["thief", "cop"]` — the **thief moves first** each turn;
- `max_moves` (25) per sub-game; if reached without capture, the **thief survives**;
- `num_games` (6) sub-games per full game;
- the **scoring table** below applied per sub-game outcome.

| Outcome | Cop | Thief |
|---|---:|---:|
| Cop captures the thief | **+20** (`cop_win`) | **+5** (`thief_loss`) |
| Thief survives 25 moves | **+5** (`cop_loss`) | **+10** (`thief_win`) |

### FR-2 → E2 — Two separate FastMCP servers with token auth
The system shall run **two independent FastMCP servers** — `cop_server` and
`thief_server` — on separate ports (`8001`, `8002` locally), each exposing role-appropriate
tools and each protected by **revocable token authentication** (`StaticTokenVerifier`, tokens
from env). Rotating a token immediately revokes access.

### FR-3 → E3 — Server/Client separation (LLM in the client)
The LLM shall live **only** in the orchestrator/MCP-Client. The MCP servers shall **never**
import or call an LLM; they expose tools and operate on game state only. This boundary is
asserted in tests and audited in Phase 12.

### FR-4 → E4 — Free natural-language communication under partial observability
On every turn an agent shall emit a **free natural-language message** (intentions, local
observations, or deception) and the receiving agent's LLM shall **interpret** it to update
its estimate of the opponent's position. No rigid numeric/coordinate protocol is permitted;
the transcript must show genuine language and at least one moment of inference from a partial
observation.

### FR-5 → E5 — Fully autonomous pipeline
A single command shall drive the entire pipeline — initialization → **6 valid sub-games** →
**automated report** — with **zero manual intervention** between init and email.

### FR-6 → E6 — Local → cloud with public HTTPS URLs
The pipeline shall be proven first on **localhost** (separate ports), then with the two MCP
servers deployed to **public HTTPS URLs** under token auth. The platform is **agnostic**
(spec §6/§7: *"Prefect Cloud or a similar platform"* plus tunneling): our simple default is a
**Cloudflare tunnel** (`cloudflared`, installed); the hosted option is **Prefect Horizon /
FastMCP Cloud** (`https://*.fastmcp.app/mcp`). The orchestrator targets cloud URLs purely via
config (`--cloud` flag).

### FR-7 → E7 — Automated Gmail JSON report
At the end of 6 valid sub-games the **Cop agent** shall **autonomously** send **one** email
whose **body is the raw JSON only** (no prose) to `rmisegal+uoh26b@gmail.com`, via the Gmail
API (`gmail.send` scope), conforming to the internal-game schema (spec §9.1):
`{group_name, students, github_repo, cop_mcp_url, thief_mcp_url, timezone, sub_games[],
totals{cop, thief}}`. A **canonical serializer** (sorted keys, fixed formatting) is used so
results are deterministic and reproducible.

### FR-8 → E8 — Config file, no hardcoding
All tunables — grid size, moves, games, barriers, scoring, ports, URLs, model, report
target, timezone, group metadata — shall live in `config/config.yaml` and be read through
`shared/config.py`. No literal of any of these may appear in code.

### FR-9 → E9 — Decision mechanism
The system shall provide a **heuristic** core (Manhattan/Chebyshev distance: cop minimizes,
thief maximizes, both operating on the **estimated** opponent cell, not ground truth), with an
**optional** tabular **Q-Table** (Bellman update, epsilon-greedy, learning-curve logging).
RL is **optional and recommended only** per spec; the heuristic alone satisfies E9, and the
Q-Table exists chiefly to produce the README's learning curve (E11).

### FR-10 → E10 — GUI + CLI logs
The system shall provide a **pygame** real-time viewer (board, cop, thief, barriers, latest
messages) for screenshots, plus structured **CLI logs** that record per turn the role, the
natural-language message, the tool call, the resulting position, and the **MCP server URL** —
proving valid communication with the (cloud) MCP servers. The GUI must be headless-safe so
the suite needs no display.

### FR-11 → E11 — Scientific Dec-POMDP README
The README shall formally model the game as a **Dec-POMDP** with the tuple
**⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩**, analyze the natural-language orchestration challenge
(ambiguity, deception, mutual understanding under partial observability), embed the
architecture/sequence diagrams, GUI screenshots, the learning curve (if used), and the
cloud-MCP CLI logs, and include the self-assessment.

### FR-12 → E12 — Inter-group bonus (optional, ready-to-activate)
The system shall include a **ready-to-activate** inter-group competition harness: a role-swap
series (our cop vs their thief ×3, then their cop vs our thief ×3) over the public cloud URLs,
producing the `bonus_game` JSON (spec §9.2: four MCP URLs, `totals_by_group`, `bonus_claim`,
`mutual_agreement`). **Both groups must email byte-identical JSON** — a mismatch scores 0 for
both — so the **same canonical serializer** as FR-7 is reused.

### FR-13 → E13 — Technical-Loss handling
Any sub-game that fails for technical reasons (a network/tool failure, not a game outcome)
shall be **voided and re-run** so that the full game always completes exactly **6 valid
sub-games**.

---

## 4. Non-Functional Requirements

- **NFR-1 — Full autonomy (zero manual intervention).** From init through 6 sub-games to the
  emailed report there shall be no human step. (Supports E5.)
- **NFR-2 — Public reachability.** The MCP URLs shall be reachable from the public internet
  (not behind a corporate firewall) with **revocable token auth**. (Supports E6.)
- **NFR-3 — Free natural-language comms.** The inter-agent channel shall be unconstrained
  natural language — no numeric protocol. (Supports E4.)
- **NFR-4 — English.** All code, docs, prompts, and the report are in English, using the spec
  vocabulary (Dec-POMDP, partial observability, MCP Server/Client separation, FastMCP, free
  natural language, orchestration, token auth, Technical-Loss).
- **NFR-5 — Deterministic, mocked tests.** The suite seeds `random`, fixes
  prompts/positions, and **mocks all LLM/MCP/network/Gmail/GUI I/O** — no live calls in CI,
  no flakes. (Supports Rule 6/17.)
- **NFR-6 — Coverage floor ≥ 85%** on game logic + config + report.
- **NFR-7 — 150-line hard cap** per `.py` file; SDK-architecture; OOP, no duplication;
  docstrings + type hints on every public signature.
- **NFR-8 — No secrets in repo.** `.env.example` only; `GEMINI_API_KEY`, MCP tokens,
  `credentials.json`/`token.json` are gitignored.
- **NFR-9 — Gatekeeper-metered LLM calls.** Every LLM call routes through
  `shared/gatekeeper.py` (token/cost meter; conversations are short, so cost ≈ 0, but always
  measured).
- **NFR-10 — Reproducibility.** A clean clone runs `uv sync` then the suite green; the full
  pipeline reproduces from config alone.

---

## 5. Success KPIs

The project is successful when **all** of the following hold:

1. **6 valid autonomous sub-games** run end-to-end over **cloud** MCP URLs with zero manual
   intervention (E5, E6, E13).
2. **Two FastMCP servers** (cop + thief) run on separate ports/URLs, each with **revocable
   token auth** (E2).
3. The two MCP servers are reachable at **public HTTPS URLs** (Cloudflare tunnel or Prefect
   Horizon) (E6).
4. The **Cop agent autonomously emails one JSON-only report** to
   `rmisegal+uoh26b@gmail.com`, schema-valid per §9.1 (E7).
5. A **scientific Dec-POMDP README** exists with the formal tuple, orchestration-challenge
   analysis, diagrams, GUI screenshots, and cloud-MCP CLI logs (E11).
6. The transcript demonstrates **free natural-language** exchange with **partial-observation
   inference** (and ideally a deception moment) (E4).
7. **Server/Client separation** verified: no LLM import/call inside `mcp_servers/` (E3).
8. **≥ 85% coverage** on game logic / config / report, all I/O mocked, deterministic (E1,
   E7, Rule 6/7).
9. **`docs/TODO.md` ≥ 600** granular `T-` tasks, distributed across phases P0–P13.
10. (Optional, bonus-ready) The inter-group harness produces a deterministic, schema-valid
    `bonus_game` JSON via the shared canonical serializer (E12).

---

## 6. Traceability Matrix (requirement → E# → phase → artifact)

| FR | Acceptance | Phase | Primary artifact(s) |
|---|---|---|---|
| FR-1 Game logic (config-driven grid, diagonal, barriers, capture, turn order, scoring) | **E1** | 2 | `src/cosmos77_ex06/game/` (board, moves, rules, match, state); `tests/unit/test_game/` |
| FR-2 Two FastMCP servers + revocable token auth | **E2** | 3 | `mcp_servers/cop_server.py`, `thief_server.py`, `tools.py` (StaticTokenVerifier) |
| FR-3 Server/Client separation (LLM in client only) | **E3** | 3, 4 | `orchestrator/`, `mcp_servers/`; Phase-12 separation assertion |
| FR-4 Free natural-language comms + partial-obs inference | **E4** | 4 | `agents/` (BaseAgent → Cop/Thief), `orchestrator/`, recorded transcripts |
| FR-5 Fully autonomous pipeline (init → 6 → email) | **E5** | 7 | `orchestrator/runner.py` |
| FR-6 Local → cloud, public HTTPS URLs | **E6** | 8 | `deploy/` (Horizon notes + `tunnel.sh`), cloud CLI logs in `assets/` |
| FR-7 Automated Gmail JSON report (cop, JSON-only body) | **E7** | 9 | `report/output.py`, `report/gmail_sender.py`, `reports/internal_game.json` |
| FR-8 Config file, no hardcoding | **E8** | 0, 2 | `config/config.yaml`, `shared/config.py` |
| FR-9 Decision mechanism (heuristic + optional Q-Table) | **E9** | 5 | `strategy/heuristic.py`, `strategy/qtable.py`, `strategy/plots.py` |
| FR-10 GUI + CLI logs proving cloud-MCP comms | **E10** | 6 | `gui/viewer.py`, `gui/render.py`, `assets/`, structured logs |
| FR-11 Scientific Dec-POMDP README | **E11** | 10 | `README.md`, `docs/PRD_dec_pomdp.md` |
| FR-12 Inter-group bonus harness (ready-to-activate) | **E12** | 11 | `bonus/series.py`, `bonus/report.py`, `reports/bonus_game.sample.json` |
| FR-13 Technical-Loss handling (void + rerun to 6) | **E13** | 7 | `orchestrator/runner.py` rerun logic |
| NFR-1 Autonomy / NFR-5 mocked tests / NFR-6 coverage | E5, Rule 6/7 | 7, 12 | `orchestrator/runner.py`, `tests/`, `docs/ACCEPTANCE.md` |
| NFR-8 No secrets / NFR-2 token auth & revocation | E2, E6 | 0, 3, 8 | `.env.example`, `.gitignore`, deploy notes |
| KPI-9 ≥600 TODO tasks | — | 1 | `docs/TODO.md` |

---

## 7. Scope, Assumptions, Out-of-Scope

**In scope.** The grid state-machine; two FastMCP servers with token auth; the
orchestrator/MCP-Client + Gemini native-MCP tool-calling loop; the free natural-language
protocol; the heuristic (and optional Q-Table); the pygame GUI; platform-agnostic public
deployment; the automated Gmail JSON report; the Dec-POMDP README; the ready-to-activate
bonus harness.

**Assumptions.** A free `GEMINI_API_KEY`; a public-reachability path (`cloudflared` default,
Prefect Horizon optional); a Google Cloud OAuth desktop client (`credentials.json`) with the
submitter added as a Test user. The build and CI need **none** of these — all live I/O is
mocked.

**Out of scope / explicitly de-emphasized.** Sophisticated pursuit strategy (the grade is
orchestration, not strategy); any LLM logic inside the MCP servers (forbidden, E3); a rigid
numeric coordination protocol (forbidden, E4); committing secrets. The Q-Table is optional and
exists mainly for the README's learning curve.

---

## 8. Risks & Mitigations (summary; full register in `docs/PLAN.md`)

- **Cloud cold-starts / changing free-tunnel URLs** → keep config the single source of
  truth; update `mcp.cop_url`/`thief_url` on each tunnel restart; Horizon as the always-on
  alternative.
- **Firewall / non-reachability** → public deploy is mandatory (E6); never rely on LAN-only.
- **Natural-language ambiguity** (E4) → robust prompts, explicit re-ask on uncertainty, and
  position-estimate updates each turn; documented in `docs/PRD_nl_protocol.md`.
- **Bonus JSON mismatch** (E12) → a single **canonical serializer** shared by both groups; a
  `diff`-check before sending; mismatch = 0 for both.
- **Free-tier rate limits** → short prompts, small dev grids, Gatekeeper metering.
- **Server/Client boundary drift** (E3) → Phase-12 static check that no LLM is imported in
  `mcp_servers/`.
