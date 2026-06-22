# PRD — Decision Strategy (Heuristic core + optional Q-Table)

> **Acceptance criterion: E9 — Decision mechanism (heuristic and/or Q-Table).**
> **Scope discipline:** the grade for HW6 (203.3763) is the *orchestration* — two autonomous
> agents coordinating in **free natural language** over **MCP servers** under **partial
> observability** — **not** the cleverness of the pursuit strategy. This document is therefore
> deliberately **proportionate**: it specifies a small, correct, fully-tested decision core and
> an *optional* tabular reinforcement-learning extension whose only job is to produce a
> learning curve for the scientific README (E11). RL is **optional per the spec** (§8:
> "אופציונלי ומומלץ בלבד" — optional and recommended only); a heuristic alone satisfies E9.

---

## 1. Purpose and design constraints

The decision mechanism answers one question per turn, for one agent:

> *Given everything I am allowed to know, which legal action should I take this turn?*

The critical phrase is **"everything I am allowed to know."** This is a **Dec-POMDP** with
**partial observability**: neither agent observes the opponent's exact cell. The strategy never
reads ground truth. It operates entirely on each agent's **estimate** of the opponent's
position — an estimate that is *inferred from the free natural-language messages* exchanged over
MCP (see `PRD_nl_protocol.md`) plus the agent's own local observation
(`get_local_observation`, which returns only a bounded local view, never the opponent's exact
cell — see `PRD_mcp_servers.md`).

Design constraints inherited from `CLAUDE.md` and the playbook §1:

| Constraint | Consequence for `strategy/` |
|---|---|
| Rule 4 — zero hardcoded config | Distance metric choice, RL hyper-parameters, epsilon schedule, all read from `config/config.yaml`. |
| Rule 1 — 150-line cap per file | `heuristic.py` ≤120, `qtable.py` ≤140, `plots.py` ≤80; split if needed. |
| Rule 6/17 — deterministic, mocked tests | Seed `random`; Bellman update checked against a hand-computed value; no LLM/network in the suite. |
| Rule 2 — SDK architecture | Strategy is a pure library; only the orchestrator/agents call it. |
| E3 — Server/Client separation | Strategy is pure Python and may be consulted by the **orchestrator/agents** (client side). It is **never** imported into `mcp_servers/`, and it never calls an LLM. |

**Boundary, restated:** the strategy module is a deterministic helper that lives on the client
side. The LLM (Gemini, in the orchestrator) is the actual decision-maker; the strategy is at
most a *suggestion* the LLM may accept or override (see §6). The strategy contains no LLM, no
MCP client, and no I/O.

---

## 2. Inputs, outputs, and the estimate

### 2.1 The estimate (the only "opponent" input)

The strategy is given an **estimated opponent cell** `est = (ex, ey)`, plus a scalar
**confidence** in `[0, 1]`. The estimate is produced upstream by the agent's LLM reasoning over:

1. the opponent's **last natural-language message** (which may be honest, vague, or a **bluff**);
2. the agent's own **partial local observation** (own position, nearby cells within a vision
   radius, visible barriers);
3. the running **transcript** (movement implied across turns).

When confidence is low, the estimate degrades gracefully to a **belief region** (a set of
plausible cells) rather than a single point; the heuristic then optimizes against the region's
centroid or worst case (§3.3). This is the strategy's contract with partial observability: it
never assumes the estimate is correct, only that it is the best available belief.

### 2.2 Strategy interface (conceptual)

```
suggest_action(role, self_pos, est_opponent, confidence, board, barriers_left) -> Action
```

- `role` ∈ {`"cop"`, `"thief"`}.
- `self_pos` — the agent's own cell (known exactly; it is *self*-observation).
- `est_opponent` — the inferred opponent cell (or belief region).
- `board` — geometry only (grid size, diagonal flag, blocked cells the agent can see).
- `barriers_left` — remaining barrier budget (cop only; `max_barriers` from config).
- returns an `Action`: a **move** (one of the legal neighbours) or, for the cop, a **barrier
  placement** on a legal empty cell.

The action is then validated and executed by the orchestrator via the agent's MCP tools
(`apply_move`, `place_barrier`). The strategy proposes; the game engine and the MCP servers
dispose.

---

## 3. Heuristic core (the required mechanism)

The heuristic is the **baseline that fully satisfies E9** on its own. It is greedy, distance-
based, and operates only on the estimate.

### 3.1 Distance metric (config-driven)

Because diagonal movement is enabled (`allow_diagonal: true`), the natural step-cost metric is
**Chebyshev distance** (king-moves):

```
chebyshev(a, b) = max(|ax - bx|, |ay - by|)
```

When diagonals are disabled the metric falls back to **Manhattan distance**:

```
manhattan(a, b) = |ax - bx| + |ay - by|
```

The choice follows `allow_diagonal` from config — no hardcoding. Both functions are pure and
trivially unit-tested.

### 3.2 Cop policy — minimize distance, then cut off escape

The cop is the **pursuer**. Per turn it:

1. Enumerates its **legal moves** (in-bounds, not into a blocked cell; diagonals if allowed).
2. Scores each candidate by the **distance to the estimated thief cell** under the active
   metric, and selects the move that **minimizes** that distance (ties broken deterministically,
   e.g. lowest `(x, y)`, for reproducible tests).
3. **Barrier reasoning (cop-only, ≤ `max_barriers`):** when the cop is **adjacent** to the
   estimated thief cell (distance ≤ 1 under the metric) — i.e. capture is imminent or the thief
   is about to slip past — the cop may instead **place a barrier** on the cell that best **cuts
   off the thief's most valuable escape route** (the empty neighbour of the estimate that most
   increases the thief's distance to open space). Barriers are impassable to **both** agents, so
   the cop weighs the trade-off: a barrier consumes budget and can also wall the cop out. The
   heuristic places a barrier only when `barriers_left > 0` **and** the cut-off measurably
   shrinks the thief's reachable open area; otherwise it moves.

**Capture** is achieved when the cop's move lands the cop **on the thief's cell** (the rule lives
in `game/rules.py`, not in the strategy). The heuristic's distance-minimization drives toward
exactly that event.

### 3.3 Thief policy — maximize distance / head to open space

The thief is the **evader**. Per turn it:

1. Enumerates its legal moves.
2. Scores each by the **distance to the estimated cop cell** and selects the move that
   **maximizes** that distance.
3. **Open-space tie-breaker:** among near-equal candidates, prefers the move with the **highest
   local freedom** — the most reachable empty cells in a small radius — so the thief drifts
   toward open areas and away from corners/walls/barriers where the cop can trap it. Reaching
   `max_moves` without capture is a **thief survival** (thief win), so maximizing distance *and*
   options is the survival objective.

### 3.4 Acting under uncertainty (belief region)

When `confidence` is low the estimate is a **region**. The cop then minimizes distance to the
region **centroid** (greedy expected pursuit) or, more cautiously, to its **nearest** plausible
cell; the thief maximizes distance to the region's **nearest** plausible cop cell (worst-case
evasion). The aggregation rule is config-selectable. This keeps the heuristic honest about the
fact that the NL-inferred estimate can be **wrong or deceptive** — the strategy is robust to a
bluff because it never treats a single message as ground truth.

---

## 4. Optional tabular Q-Table extension (RL — *optional per spec*)

> **This section is optional.** It exists to produce the **learning curve**
> (`assets/learning_curve.png`) referenced by the scientific README (E11) and to demonstrate a
> decision mechanism that *learns*. It is **not required** for E9 — the §3 heuristic already
> satisfies it. We include a minimal version as cheap insurance for completeness, not because
> the grade depends on strategy quality.

### 4.1 State, action, reward

- **State** — a compact, discrete encoding of `(self_pos, est_opponent, barriers_left)` (and,
  for the cop, whether the thief is cornered). The estimate — not ground truth — is part of the
  state, keeping the learner inside the partial-observability regime.
- **Action** — the same action set as the heuristic: the legal moves, plus (cop only) barrier
  placements.
- **Reward `r`** — shaped from the config **scoring table** (`cop_win: 20`, `thief_win: 10`,
  `cop_loss: 5`, `thief_loss: 5`) at terminal states, with a small per-step shaping toward the
  heuristic objective (e.g. `-Δdistance` for the cop, `+Δdistance` for the thief) to speed
  convergence on the tiny default 5×5 board.

### 4.2 Bellman update and exploration

Tabular Q-learning with the standard temporal-difference update:

```
q[s, a] += alpha * (r + gamma * max_a' q[s', a'] - q[s, a])
```

- `alpha` (learning rate), `gamma` (discount), and the **epsilon** schedule are read from
  `config/config.yaml` — no hardcoded hyper-parameters (Rule 4).
- Action selection is **epsilon-greedy**: with probability `epsilon` pick a random legal action
  (explore), otherwise pick `argmax_a q[s, a]` (exploit). `epsilon` decays per episode from a
  configured start to a configured floor.

### 4.3 Episode-reward logging and the learning curve

- Each training **episode** (a self-play sub-game on a small grid) logs its **total reward** to
  a results file under `paths.results`.
- `strategy/plots.py` renders the per-episode reward (and a moving average) with matplotlib to
  `assets/learning_curve.png` — the figure embedded in the README (E11) to evidence learning.
- Training is **offline and self-play**; it never calls Gemini or any MCP server. It is gated
  behind a config flag / CLI option so the default autonomous pipeline (E5) does **not** depend
  on it.

### 4.4 Determinism for tests

The Bellman update is verified against a **hand-computed** numeric example; epsilon-greedy is
tested with a seeded RNG to assert the explore/exploit split matches the configured `epsilon`.
No flakes (Rule 17).

---

## 5. How the strategy maps to acceptance criteria

| Criterion | How this strategy satisfies it |
|---|---|
| **E9 — decision mechanism** | Heuristic (Manhattan/Chebyshev) is the required core; the optional Q-Table is the "and/or Q-Table" half. |
| **E4 — free NL + partial obs** | The strategy consumes only the **estimate** inferred from NL messages + local observation — never ground truth. It is robust to bluffing (§3.4). |
| **E8 — config, no hardcoding** | Metric (via `allow_diagonal`), `max_barriers`, scoring-derived reward, and all RL hyper-parameters come from `config/config.yaml`. |
| **E3 — Server/Client separation** | Pure client-side library; no LLM, no MCP, never imported into `mcp_servers/`. |
| **E11 — scientific README** | Q-Table episode log → `assets/learning_curve.png`; the heuristic is described in the strategy section of the README. |

---

## 6. Suggestion vs. authority — is the strategy binding?

**The strategy is a *suggestion*, not the decision-maker.** The actual per-turn decision is made
by **Gemini in the orchestrator** (the MCP Client). Two integration modes are supported, and the
project documents which is active here and why:

1. **LLM-direct.** Gemini chooses the action straight from the prompt (partial observation +
   opponent's last NL message), with **no** strategy consultation. This is the purest expression
   of the graded goal — autonomous agents *reasoning in natural language* — and demonstrates the
   orchestration without leaning on a hand-coded policy.

2. **Strategy-as-tool (suggested action).** The heuristic (or the trained Q-Table) is exposed to
   the agent as a **suggested action** the LLM may **accept or override**. The LLM still owns the
   final decision and still emits a free-language message; the suggestion only grounds its
   reasoning and reduces obviously-bad moves on a tiny grid.

**Chosen default and rationale.** We default to **strategy-as-suggestion**: the LLM remains the
authority (preserving the natural-language, autonomous-agent character the grade rewards), while
the cheap heuristic keeps moves sane within free-tier rate limits and short conversations. The
LLM is explicitly permitted to **override** the suggestion — e.g. when the NL evidence suggests
the opponent bluffed and the geometric estimate is unreliable. We do **not** let the strategy
silently dictate moves, because that would hollow out the orchestration the assignment is
actually grading. This choice, and the override behaviour, is mirrored in the agent prompt
construction (`agents/base.py`, Phase 4) and re-stated in the README.

---

## 7. File plan (`src/cosmos77_ex06/strategy/`)

| File | Responsibility | Cap |
|---|---|---|
| `heuristic.py` | Distance metrics (Chebyshev/Manhattan), cop/thief policies, barrier cut-off reasoning, belief-region aggregation. **Required.** | ≤120 |
| `qtable.py` | Tabular Q-learning: state encoding, Bellman update, epsilon-greedy, episode-reward logging. **Optional.** | ≤140 |
| `plots.py` | matplotlib learning curve → `assets/learning_curve.png`. **Optional** (only if Q-Table used). | ≤80 |

All public classes/functions carry docstrings (Rule 15) and type hints (Rule 16). Tests live in
`tests/unit/test_strategy/`: heuristic moves provably reduce/increase distance on fixture
boards; the barrier rule fires only when adjacent and budget remains; the Bellman update matches
the hand-computed value; epsilon-greedy explores vs exploits as configured.

---

## 8. Summary

The decision mechanism is intentionally small. A **distance-greedy heuristic** — cop minimizes,
thief maximizes, cop cuts off escape with a barrier when adjacent — operating on an
**NL-inferred estimate** rather than ground truth, fully satisfies **E9** under partial
observability. An **optional tabular Q-Table** (Bellman, epsilon-greedy, config hyper-params,
episode-reward logging) adds a learning curve for the README but is **not required by the spec**.
Above all, the strategy is a **suggestion** that the orchestrator's LLM may accept or override:
the autonomous, natural-language **orchestration** — not the policy — is what the assignment
grades, and this module is deliberately scoped to stay out of its way.
