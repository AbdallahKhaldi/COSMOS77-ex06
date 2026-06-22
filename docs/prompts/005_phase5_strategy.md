# Phase 5 — Decision strategy (E9)

> Prompt log for the Phase-5 build: the decision mechanism (heuristic core + optional
> tabular Q-Table). Scope kept **proportionate** — HW6's grade is the *orchestration*,
> not the pursuit strategy (PRD_strategy §0). Pure Python, fully tested, no live
> LLM/MCP/network.

## What I built

### `src/cosmos77_ex06/strategy/`

| File | Lines | Responsibility |
|---|---|---|
| `heuristic.py` | 117 | Distance metrics (Chebyshev when `allow_diagonal`, else Manhattan), `suggest_cop_action` (minimize distance to the **estimate**; place a barrier to cut off escape when adjacent + budget remains), `suggest_thief_action` (maximize distance, open-space tie-break). Operates only on the agent's **estimate**, never ground truth. Config-driven. |
| `qtable.py` | 91 | Tabular Q-Learning: `Q[(state, action)]` dict, `select_action` (epsilon-greedy), `update` (the exact Bellman temporal-difference rule), per-episode reward logging. Hyper-parameters (alpha/gamma/epsilon/episodes) read from `config.qlearning`. |
| `plots.py` | 62 | Headless-safe matplotlib learning curve → `assets/learning_curve.png`. Forces the `Agg` backend and lazy-imports matplotlib inside the function; the `savefig` side effect is `# pragma: no cover`. |

### Integration (optional, config-gated, DEFAULT-OFF)

- `agents/base.py` — `build_prompt(observation, opponent_message, suggestion=None)` gained an
  **optional** `suggestion` argument. When `None` (the default) the prompt is byte-identical to
  the Phase-4 prompt; when a suggestion is supplied a single `HINT (...accept or override it)`
  line is appended. The heuristic is the *suggestion*; the LLM remains the decision-maker (PRD §6).
- The belief logic (`interpret` / `_opponent_cell`) was extracted into a `BeliefMixin`
  (`agents/belief.py`) so `base.py` stays under the 150-line cap after the new prompt argument
  (Rule 1 / Rule 3, no behaviour change — `agent.interpret(...)` callers are unchanged).
- Gate: `strategy.enabled` in `config/config.yaml`, shipped `false`. Phase-4 behaviour and all
  Phase-4 tests are unchanged.

### Config keys added (`config/config.yaml`, Rule 4 — nothing hardcoded)

```yaml
strategy:
  enabled: false          # default-off optional heuristic-hint integration

qlearning:
  learning_rate: 0.1      # alpha
  discount_factor: 0.9    # gamma
  epsilon: 0.1            # epsilon-greedy exploration probability
  episodes: 200           # training episodes for the learning curve
```

## Bellman update — hand-computed verification

The spec rule (best_next_q = 0 when `done`):

```
q[s,a] <- q[s,a] + alpha * (reward + gamma * max_a' q[s',a'] - q[s,a])
```

**Non-terminal example** (`tests/.../test_qtable.py::test_bellman_update_matches_hand_computed_value`):

| symbol | value |
|---|---|
| alpha | 0.5 |
| gamma | 0.9 |
| q[s,a] (before) | 2.0 |
| reward | 1.0 |
| max_a' q[s',a'] | 5.0 (over `{x:5.0, y:4.0}`) |
| done | False |

```
q' = 2.0 + 0.5 * (1.0 + 0.9*5.0 - 2.0)
   = 2.0 + 0.5 * (1.0 + 4.5 - 2.0)
   = 2.0 + 0.5 * 3.5
   = 2.0 + 1.75
   = 3.75   ✓ asserted exactly
```

**Terminal example** (`::test_bellman_update_drops_bootstrap_when_done`) — bootstrap dropped:

```
q' = 2.0 + 0.5 * (1.0 + 0.9*0 - 2.0)
   = 2.0 + 0.5 * (-1.0)
   = 1.5    ✓ asserted exactly (the 5.0 next-state value is correctly ignored)
```

## Tests (`tests/unit/test_strategy/`, deterministic + seeded)

- `test_heuristic.py` — cop move provably reduces distance to the estimate; thief move increases
  it; Manhattan vs Chebyshev metric switch; open-space tie-break; barrier fires only when adjacent
  with budget and >1 escape; STAY fallback when walled-in.
- `test_qtable.py` — the two hand-computed Bellman assertions above; unseen pairs default to 0;
  epsilon-greedy: `epsilon=0` always exploits the argmax (seeded), `epsilon=1` always explores
  (reaches every action); empty-action guard; episode logging; hyper-parameters read from config.
- `test_plots.py` — headless smoke test that the PNG is produced (Agg, tmp path); moving average;
  Agg backend assertion; empty-input guard.
- `test_agent_hint.py` — prompt is byte-identical with no suggestion (Phase-4 unchanged); the HINT
  is appended when a suggestion is passed; `strategy.enabled` is `false` by default.

## Gate results (all green)

- `uv run ruff check .` → All checks passed!
- `uv run ruff format --check .` → 90 files already formatted
- `uv run python scripts/check_line_cap.py` → OK (every file ≤ 150 lines)
- `uv run pytest -q -m 'not live'` → 221 passed, 1 deselected; total coverage 99.27% (≥ 85%);
  strategy modules at 100%.
