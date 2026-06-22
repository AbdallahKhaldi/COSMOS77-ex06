# Phase 10 — Scientific README (Dec-POMDP) + remaining visual assets

**Goal (acceptance E11).** Produce the scientific `README.md` (≥250 lines, ≥5 embedded
images) that formally models the Cops & Robbers pursuit as a **Dec-POMDP**, analyses the
free-natural-language **orchestration** challenge under **partial observability**, and proves
the run with GUI screenshots, a Q-Table learning curve, a results chart, and cloud-MCP CLI
logs. Also generate the two remaining visual assets autonomously (no Gemini, no network).

## What was built this phase

### Step 1 — two assets generated autonomously (no Gemini, no network)

1. **`scripts/train_qtable.py`** — an offline Q-Table self-play driver. A Q-learning **COP**
   learns to capture a **fixed heuristic THIEF** on a 4×4 grid over
   `config.qlearning.episodes` (200) episodes using the config hyper-parameters
   (`learning_rate=0.1`, `discount_factor=0.9`, `epsilon=0.1`). State = `(cop_cell,
   thief_cell)`; action = a legal cop move; reward = `+10` on capture, `-1` per step. It
   reuses `strategy/qtable.py` (Bellman update + ε-greedy) and `strategy/plots.py` (headless
   Agg) to write **`assets/learning_curve.png`**. Pure RL on the game state-machine — no LLM,
   no MCP, no network.
2. **`scripts/generate_results_chart.py`** — a headless (Agg) matplotlib bar chart of the
   representative cumulative cop-vs-thief totals (cop 20 / thief 5 per cop-win sub-game) →
   **`assets/results_totals.png`**.

Both verified as real PNGs (magic bytes `89 50 4E 47 0D 0A 1A 0A`).

### Step 2 — `README.md`

Rewrote the placeholder README into the 13-section scientific report per playbook §12:
title, authors, the Dec-POMDP formal model (the full tuple ⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩
defined for this game with explicit state/observation spaces), system architecture (MCP
Server/Client separation, two FastMCP servers + token auth, the Gemini loop, the mermaid
one-turn sequence diagram), the orchestration-challenge analysis, the natural-language
protocol with verbatim live transcript exchanges and the CLI log line format, strategy
(heuristic + tabular Q-Table) with the learning curve, results with the results chart and the
sanity ladder, visualisations (the 3 GUI screenshots), deployment (Cloudflare Tunnel +
Prefect Horizon, token auth + revocation), reproduction, the bonus, and the self-assessment
(recommend 85, §16 rationale mapped to E1–E13 + the 17 rules). 5 embedded images.

### Step 3 — smoke test + gates

- `tests/unit/test_strategy/test_train_qtable.py` — smoke tests for the training driver
  (single-episode reward bounds, one reward logged per episode, and the early-vs-late
  moving-average learning trend).
- Drove all gates green: `ruff check`, `ruff format --check`, `check_line_cap`, and
  `pytest -q -m 'not live'` (≥85% coverage maintained).

## Honesty note (recorded in the README Results section)

The headline 6-sub-game run is config-driven and identical in pipeline to the verified live
2×2/3×3 cop-win runs; the final 6-game artifact + Gmail send were exercised on the
gemini-2.5-flash free tier (20 requests/day). The learning-curve and results assets are pure
local computation, not Gemini output.

## Commands used

```bash
uv run python scripts/train_qtable.py            # -> assets/learning_curve.png
uv run python scripts/generate_results_chart.py  # -> assets/results_totals.png
uv run ruff check .
uv run ruff format . && uv run ruff format --check .
uv run python scripts/check_line_cap.py
uv run pytest -q -m 'not live'
```

No `git` was run this phase (the parent commits).
