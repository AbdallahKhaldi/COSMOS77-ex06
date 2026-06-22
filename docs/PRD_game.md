# PRD — Game Mechanism (the grid state-machine)

> **Scope.** This PRD specifies the *pure*, deterministic grid state-machine for COSMOS77-ex06
> — the Cops & Robbers pursuit at the heart of HW6 (Orchestration of AI Agents, 203.3763).
> It covers the board model, movement, barriers, capture, survival, turn order, the
> sub-game/game hierarchy, the scoring table, the serializable `GameState`, and the 4-stage
> sanity ladder. It maps to acceptance criterion **E1** (game logic) and **E8** (config-driven,
> no hardcoding), and feeds **E5/E7/E10/E11** by producing the `GameState` the orchestrator,
> GUI, and report all read.

> **Where this sits in the grade.** The professor says it four times: **the grade is the
> orchestration, not the game strategy.** The game logic is therefore *plumbing* — it must be
> rigorously correct, fully deterministic, and exhaustively tested, but it carries no LLM and
> no cleverness. It is the referee, not a player. All decision-making (and all natural-language
> reasoning under partial observability) lives in the orchestrator/agents; this module only
> *enforces the rules* and *records ground truth*. Critically, this module also defines the
> **ground-truth** the MCP servers must never leak in full: an agent's tool only ever sees a
> *partial* projection of the `GameState` (its own position + a local neighbourhood), which is
> what makes the pursuit a genuine **Dec-POMDP** with **partial observability**.

---

## 1. Design principles

1. **Pure Python, zero side effects.** No LLM, no MCP, no network, no I/O. Given a state and a
   move, the machine returns a new state (or mutates a single owned state object) and nothing
   else. This makes it trivially unit-testable and deterministic (Rule 17 — seed `random`).
2. **Config-driven, no hardcoding (Rule 4 / E8).** Every tunable — `grid_size`, `max_moves`,
   `num_games`, `max_barriers`, `allow_diagonal`, `turn_order`, and the full `scoring` table —
   is read from `config/config.yaml` via `shared/config.py`. No literal `5`, `25`, `6`, `20`
   appears in `game/`. The sanity ladder works *only* because every dimension is a config knob.
3. **Single source of truth for state.** Exactly one serializable object, `GameState`, is the
   board's truth. The GUI reads it; the report serializes from it; the MCP tools project a
   *partial* view of it. There is no second representation to drift out of sync.
4. **Referee, not player.** The machine validates and applies; it never *chooses*. It exposes
   `legal_moves(...)` so callers can decide, and rejects illegal actions deterministically.
5. **150-line cap (Rule 1).** The mechanism is split across `board.py`, `moves.py`,
   `rules.py`, `match.py`, and `state.py` (file responsibilities in §11).

---

## 2. Coordinates and the board model

### 2.1 Coordinate system

A cell is an integer pair `(x, y)` — **column `x`, row `y`** — with the origin `(0, 0)` at the
top-left. For a board of `grid_size = [W, H]` (width `W`, height `H`):

- `x ∈ {0, …, W-1}` (columns), `y ∈ {0, …, H-1}` (rows).
- The default board is `5 × 5`; the sanity ladder overrides this to `2×2`, `3×3` (or `3×2`),
  `4×4` (or `4×3`), then `5×5` — all via config, never via code (§9).

`grid_size` is read as `[W, H]`. Non-square boards (e.g. `3×2`, `4×3`) are explicitly
supported by the ladder, so the board model never assumes `W == H`.

### 2.2 `Board`

`game/board.py` holds an immutable-by-construction `Board` built from config:

- **`width`, `height`** — from `grid_size`.
- **`allow_diagonal`** — from config; controls the neighbour function (8-connected vs
  4-connected).
- **`barriers: set[tuple[int,int]]`** — the set of blocked cells. Starts empty; the cop adds to
  it during a sub-game (§4). A cell in `barriers` is impassable to **both** agents and behaves
  exactly like an out-of-bounds edge.

Core predicates:

| Method | Meaning |
|---|---|
| `in_bounds((x,y))` | `0 ≤ x < width and 0 ≤ y < height` |
| `is_blocked((x,y))` | `(x,y) in barriers` |
| `is_passable((x,y))` | `in_bounds((x,y)) and not is_blocked((x,y))` |
| `neighbors((x,y))` | the passable cells reachable in one step (see §3) |

### 2.3 Movement directions

Directions are named deltas, resolved once from `allow_diagonal`:

- **Orthogonal (always):** `N(0,-1)`, `S(0,+1)`, `E(+1,0)`, `W(-1,0)`.
- **Diagonal (only when `allow_diagonal: true`):** `NE(+1,-1)`, `NW(-1,-1)`,
  `SE(+1,+1)`, `SW(-1,+1)`.
- **`STAY(0,0)`** is permitted (an agent may hold position; it is always "legal" provided the
  current cell is passable, which it always is).

With the project default `allow_diagonal: true`, each agent has up to **9** candidate actions
per turn (8 moves + stay), pruned to the legal subset by §3.

---

## 3. Movement in all eight directions

`game/moves.py` provides the movement contract over a `Board`:

- **`legal_moves(pos, board) -> list[direction]`** — the directions whose target cell is
  *passable*. A target is passable iff it is in-bounds **and** not a barrier. When
  `allow_diagonal` is false, the four diagonal directions are never offered. `STAY` is always
  included (subject to the current cell being passable, which it is by invariant).
- **`apply_move(pos, direction, board) -> new_pos`** — returns the target cell if and only if
  the move is legal; raises a deterministic `IllegalMoveError` otherwise. The machine never
  silently clamps an illegal move — an out-of-bounds or into-barrier attempt is a hard error so
  the orchestrator/agent logic is forced to be correct (and so a Technical-Loss can be detected,
  §6.4).

**Diagonal semantics.** A diagonal step moves one cell on each axis simultaneously
(Chebyshev/king move). Diagonals are **not** subject to a "corner-cutting" rule: a cell is
reachable diagonally even if the two orthogonally-adjacent cells are barriers — the only test
is whether the *destination* itself is passable. This keeps the rule set minimal and is the
behaviour assumed by the heuristic strategy (Manhattan/Chebyshev distance, see
`docs/PRD_strategy.md`).

**Edge = barrier.** From the agent's perspective the board edge and a barrier are
indistinguishable: both simply remove a direction from `legal_moves`. This uniformity is what
lets a barrier act "like a wall/edge".

---

## 4. Barrier placement (cop-only)

Barriers are the cop's structural tool — the spatial counterpart to the cop's faster
information advantage.

- **Who:** **only the cop** may place barriers. Any attempt by the thief is illegal.
- **How many:** at most **`max_barriers`** (config default `5`) **per sub-game**. The counter
  resets each sub-game. Exceeding the budget is illegal.
- **Where:** on an **in-bounds, currently-passable** cell that is **not** the cop's own cell and
  **not** the thief's current cell (a barrier cannot be dropped *onto* an agent). Re-blocking an
  already-blocked cell is a no-op error (wastes nothing; just rejected).
- **Effect:** the cell is added to `board.barriers` and becomes **impassable for both agents**,
  permanently for the remainder of that sub-game — exactly like a wall or the board edge. It is
  removed when the next sub-game resets the board.

`game/moves.py::place_barrier(role, cell, board, barriers_used)` enforces the role check, the
budget, and the passability/occupancy check, then mutates `board.barriers` and increments the
sub-game barrier counter. It is a *separate action* from a move: in a given turn the cop's tool
call either moves or places a barrier (the action taxonomy the MCP tools expose — see
`docs/PRD_mcp_servers.md`). The strategy layer may, for example, drop a barrier to cut off a
thief's escape corridor when adjacent (see `docs/PRD_strategy.md`).

> **Why cop-only and shared-impassable matters for the Dec-POMDP.** Barriers shrink the
> *transition* space `P` for both players and are *observable structure*. They are part of the
> ground-truth `GameState` but are only partially observed by each agent (an agent learns a
> barrier exists when it appears in the agent's local view or is inferred from the opponent's
> natural-language message — see `docs/PRD_nl_protocol.md`).

---

## 5. Capture detection and thief survival

`game/rules.py` owns the two terminal conditions:

- **Capture (cop wins the sub-game).** Capture occurs the instant the **cop lands exactly on
  the thief's cell** — `cop_pos == thief_pos`. Because the thief moves first within a turn
  (§6.1), capture is tested *after the cop's move resolves*. (A subtle but graded detail: the
  cop captures by *landing on* the thief; the thief stepping onto the cop's cell is not a
  capture — but with thief-first ordering the thief never benefits from this, and the cop's
  subsequent move is what closes the distance.)
- **Survival (thief wins the sub-game).** If the sub-game reaches **`max_moves`** (config
  default `25`) turns with **no capture**, the **thief survives** and wins the sub-game.

`rules.py` exposes:

- `is_capture(state) -> bool` — `state.cop_pos == state.thief_pos`.
- `is_survival(state) -> bool` — `state.move_number >= max_moves` and not captured.
- `subgame_result(state) -> {"cop_win" | "thief_win"}` and the per-role score lookup (§7).

There is no draw in a sub-game: every sub-game terminates either in capture (cop_win) or at the
move limit (thief_win). This binary outcome is what makes the scoring table (§7) total cleanly.

---

## 6. Turn order, sub-games, and the full game

### 6.1 Turn order — **thief then cop**

`turn_order: ["thief", "cop"]` from config: the **thief moves first**, then the cop, and the
pair constitutes one **turn** (one increment of `move_number`). After each agent acts, the
machine checks the terminal conditions in order:

1. thief acts (move / stay) — board updates;
2. (capture is *not* possible from the thief's own move under the standard cop-captures rule);
3. cop acts (move / stay / place barrier) — board updates;
4. **capture check** (`cop_pos == thief_pos`) → if true, sub-game ends, **cop_win**;
5. else **limit check** (`move_number == max_moves`) → if true, sub-game ends, **thief_win**;
6. else `move_number += 1`, next turn.

The thief moving first gives the *pursued* the initiative each turn — a deliberate asymmetry
that makes capture non-trivial and the orchestration interesting.

### 6.2 Sub-game (≤ 25 moves)

A **sub-game** is one pursuit episode: a fresh board (barriers cleared, barrier-budget reset),
fresh start positions, `move_number = 0`, run until capture or `max_moves`. `game/match.py`'s
`SubGame` drives the turn loop, records a **per-move log** (turn #, role, action, resulting
position, and the agents' natural-language messages threaded in from the orchestrator), and
returns a `SubGameResult` (winner, per-role score, move count, final `GameState`, full log).

### 6.3 Game (6 sub-games, totals accumulated)

A **full game** is **`num_games` = 6** sub-games. `game/match.py`'s `Game` runs the six
sub-games and **accumulates per-role totals** by summing the per-sub-game scores from the
scoring table (§7). Because each sub-game contributes to exactly one of `{cop_win, thief_win}`
and each side also takes its corresponding loss/penalty value, the per-game totals fall in the
spec's expected band (game max **90** / min **30** across the six sub-games). The accumulated
totals `{cop: int, thief: int}` are exactly what the internal-game JSON report (`§9.1` schema,
see `docs/PRD_report.md`) carries.

### 6.4 Technical-Loss (E13)

A sub-game that fails **technically** (an unrecoverable orchestration/transport error — e.g. a
cloud MCP timeout, an `IllegalMoveError` the engine cannot recover, an agent that never
produces a valid action) is **voided** — it does **not** count toward the six valid sub-games.
`game/match.py` flags such a sub-game (`technical_loss: true`) so the runner
(`orchestrator/runner.py`, Phase 7) **re-runs** until **6 valid sub-games** complete. The game
state-machine's job here is narrow but essential: surface a clean, typed failure signal
(`TechnicalLoss`) that the runner can detect and act on, never a corrupted half-counted result.

---

## 7. The scoring table

All four values come from `config.yaml::scoring` (no hardcoding):

| Sub-game outcome | Cop receives | Thief receives | Rule fired |
|---|---|---|---|
| **Cop captures the thief** (`cop_pos == thief_pos`) | **`cop_win` = 20** | **`thief_loss` = 5** | capture (§5) |
| **Thief survives to `max_moves`** | **`cop_loss` = 5** | **`thief_win` = 10** | survival (§5) |

Notes:

- A capture is worth **20** to the cop and the thief still banks a **5** consolation
  (`thief_loss`) — losing is not zero.
- A survival is worth **10** to the thief and the cop banks a **5** consolation (`cop_loss`).
- Per sub-game the combined payout is either `20 + 5 = 25` (capture) or `5 + 10 = 15`
  (survival); across six sub-games totals therefore range from `6 × 15 = 90` (all-survival is
  not the max — see below) … the spec's stated **game band is max 90 / min 30**, consistent
  with mixing the two outcome payouts across the six sub-games.
- `subgame_result → score` is a pure config lookup in `rules.py`; `Game` sums per role into
  `totals = {"cop": Σcop, "thief": Σthief}`.

`rules.py` performs the mapping with a single config-driven dictionary so changing the spec's
numbers is a one-line YAML edit with zero code change (E8).

---

## 8. The serializable `GameState`

`game/state.py` defines the **single state object** the GUI and report read, and the object the
MCP servers project a *partial* view of. It is plain, JSON-serializable data (a frozen/`pydantic`
or dataclass with a `to_dict()` / `from_dict()` round-trip):

```text
GameState
├── grid_size:    [W, H]                 # echoed from config for self-describing state
├── cop_pos:      (x, y)
├── thief_pos:    (x, y)
├── barriers:     [ (x, y), ... ]        # serialized as a sorted list for determinism
├── move_number:  int                    # 0-based turn counter, < max_moves
├── max_moves:    int                    # echoed from config
├── allow_diagonal: bool
├── turn_order:   ["thief", "cop"]
├── current_role: "thief" | "cop"        # whose action is next within the turn
├── messages:     [ {turn, role, text}, ... ]   # the free natural-language transcript
├── status:       "active" | "cop_win" | "thief_win" | "technical_loss"
└── scores:       {"cop": int, "thief": int}     # running sub-game/accumulated totals
```

Key properties:

- **Deterministic serialization.** `barriers` and `messages` serialize in a fixed order so the
  same logical state always produces byte-identical JSON. This is reused by the **canonical
  serializer** (Phase 9 / Phase 11) that lets the bonus partner emit a *byte-identical* report
  (mismatch → 0 for both groups).
- **Self-describing.** It carries `grid_size`, `max_moves`, `allow_diagonal`, and `turn_order`
  so a reader (GUI, report, a partner group) needs no external config to interpret it.
- **Partial-view source.** The MCP tool `get_local_observation(role)` derives a *masked*
  `GameState` from this object — own position + a local neighbourhood, with the opponent's exact
  cell **omitted** — which is the observation `Ωi / O` of the Dec-POMDP. The full `GameState` is
  ground truth held by the engine only; it is **never** returned wholesale by a server tool.
- **Message channel.** `messages` is where the agents' **free natural-language** turns are
  recorded (intentions, local observations, even deception) for the transcript the README and
  GUI display — the protocol itself is specified in `docs/PRD_nl_protocol.md`.

---

## 9. The 4-stage sanity ladder

Before any cloud run, the pipeline is validated on a deliberately escalating ladder of board
sizes (spec §4.5). Each rung is a pure config override of `grid_size` (and nothing else), proving
that the state-machine is genuinely config-driven and that the orchestration scales from a
trivial to the full board. A transcript per rung is saved to `reports/`.

| Stage | `grid_size` | What it validates |
|---|---|---|
| **1** | **2×2** (4 cells) | Smallest non-trivial board. Validates the *plumbing*: turn order (thief then cop), capture detection, the move limit, and the scoring lookup — with a search space so small that the orchestration loop, the MCP round-trips, and the report wiring can be eyeballed move-by-move. Capture is near-immediate; this rung is about *correctness of the machine*, not strategy. |
| **2** | **3×3 (or 3×2)** | First board with a real *interior*. Validates **diagonal movement** (a center cell now has up to 8 neighbours) and **barrier placement** changing reachable cells. Non-square `3×2` proves the model never assumes `W == H`. |
| **3** | **4×4 (or 4×3)** | Enough room that the thief can plausibly *survive to `max_moves`*. Validates the **survival/thief-win** path and that **multiple barriers** (up to `max_barriers`) meaningfully reshape the board. Both terminal outcomes (capture and survival) are now reachable, exercising both rows of the scoring table. |
| **4** | **5×5** (default) | The full target board. Validates the **end-to-end autonomous pipeline** under partial observability at production scale: genuine free natural-language exchange, position inference from text, the heuristic/Q-Table decisions, the 6-sub-game accumulation, and the automated report — the configuration that ships and that the README's results section reports. |

The ladder is also the debugging order: a failure at stage *k* is diagnosed before advancing to
*k+1*, so a problem at full scale is never confused with a problem in the rules themselves.

---

## 10. Acceptance-criteria mapping

| Criterion | How this mechanism satisfies it |
|---|---|
| **E1 — Game logic** | Config-driven grid (§2), 8-direction movement when `allow_diagonal` (§3), cop-only impassable-to-both barriers ≤ `max_barriers` (§4), capture = cop lands on thief (§5), thief survival at `max_moves` (§5), turn order thief→cop (§6.1), ≤25-move sub-games × 6 (§6.2–6.3), full scoring table (§7). |
| **E8 — Config, no hardcoding** | Every dimension/limit/score read from `config.yaml` via `shared/config.py`; the sanity ladder is pure config override (§9). |
| **E13 — Technical-Loss** | `match.py` flags `technical_loss`; voided sub-games don't count; the runner re-runs to 6 valid (§6.4). |
| **E5 / E7 / E10 / E11 (fed)** | `GameState` (§8) is the single object the orchestrator advances, the GUI renders, and the report serializes — and whose *partial projection* the MCP tools expose, realizing the Dec-POMDP's partial observability. |

---

## 11. Module responsibilities (≤ 150 lines each — Rule 1)

| File | Responsibility | Cap |
|---|---|---|
| `game/board.py` | `Board` from config; `in_bounds`, `is_blocked`, `is_passable`, `neighbors` (8-/4-connected per `allow_diagonal`); the barrier set. | ≤ 140 |
| `game/moves.py` | Direction table; `legal_moves`, `apply_move` (raises `IllegalMoveError`), `place_barrier` (cop-only, budget, passability). | ≤ 120 |
| `game/rules.py` | `is_capture`, `is_survival`, `subgame_result`, the config-driven scoring lookup, turn-order helper. | ≤ 130 |
| `game/match.py` | `SubGame` (≤ `max_moves`, per-move log, result) and `Game` (`num_games` sub-games, totals); Technical-Loss void + flag. | ≤ 140 |
| `game/state.py` | The serializable `GameState` (positions, barriers, `move_number`, messages, status, scores) + `to_dict`/`from_dict`. | ≤ 80 |

The mechanism is wired into the SDK (`SDK.new_game()`, `SDK.step(...)`) so the CLI, GUI, and
orchestrator call **only** the SDK (Rule 2). No LLM, MCP, or I/O ever enters `game/`.

---

## 12. Test obligations (Phase 2 — TDD, ≥ 90% coverage on `game/`)

Deterministic unit tests (seed `random`), all I/O-free:

- Capture triggers exactly when the cop lands on the thief's cell; not when the thief steps
  elsewhere.
- A barrier blocks **both** agents (thief and cop) and behaves like the edge.
- Thief wins when a sub-game reaches `max_moves` with no capture.
- Diagonal moves are legal **iff** `allow_diagonal: true`; the four diagonals vanish when false.
- Non-square boards (`3×2`, `4×3`) behave correctly (no `W == H` assumption).
- `place_barrier` rejects: a thief caller, the `max_barriers + 1`-th barrier, an out-of-bounds
  cell, an occupied cell, and a re-block.
- Scoring matches the table for both outcomes; a full 6-sub-game `Game` accumulates correct
  totals within the 30–90 band.
- A Technical-Loss sub-game is voided and flagged for re-run; it does not count toward the six.
- `GameState.to_dict()/from_dict()` round-trips losslessly and serializes deterministically
  (sorted barriers/messages → byte-stable JSON).
