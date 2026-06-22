# Prompt log — Phase 2: Game logic + rules (pure, fully tested)

**Goal.** The grid state-machine (acceptance E1, E8, E13): pure Python, config-driven, no
LLM/MCP — deterministic and exhaustively unit-tested. Playbook §4, design in `docs/PRD_game.md`.

## Approach — build → adversarial review → fix
Executed as a three-stage workflow:
1. **Build (TDD).** A worker implemented `game/{board,moves,rules,match,state}.py` and wired
   `SDK.new_game()` / `SDK.step()`, with an exhaustive deterministic test suite, driving every
   gate green (game/ 100% coverage).
2. **Adversarial review.** A reviewer tried to break it against the spec rules and the 17 rules,
   defaulting every compliance flag to *false* unless proven by code/tests.
3. **Fix.** A worker applied real fixes for every finding and re-greened all gates.

## What the review caught (and the fix resolved — no test masking)
- **HIGH — survival predicate divergence (dead code):** `rules.is_survival` used
  `move_number >= max_moves`, but the engine's terminal `move_number` never reached `max_moves`
  (it checked `move_number + 1 >= max_moves` *before* incrementing), so `is_survival(final_state)`
  returned `False` and was effectively dead. **Fix:** the engine now increments `move_number`
  *before* the survival check and uses `rules.is_survival` as the single terminal predicate.
- **HIGH — `move_count` off-by-one on survival:** reported `max_moves-1` while `max_moves` turns
  were actually played (would corrupt Phase-4 transcript/report move accounting). **Fix:** count
  now reflects the true number of completed turns; locked with an explicit assertion.
- **MEDIUM — false "30–90 band" claim in PRD_game:** with cop_win=20/cop_loss=5 the cop's
  six-sub-game range is **30–120** (thief 30–60). **Fix:** corrected the PRD to the true per-role
  bands; replaced the misleading shared-band test with real per-role bounds.
- **MEDIUM — untested graded subtleties:** thief *stepping onto* the cop's cell is **not** a
  capture; per-sub-game barrier-budget/board **reset**. **Fix:** both now asserted.
- **LOW — `max_moves<=0` forced-turn edge, SDK conflating `len(barriers)` with the per-sub-game
  budget, missing meta-rule coverage.** **Fix:** added a guard, a dedicated `barriers_used`
  field on `GameState`, and `test_meta_rules.py` asserting line caps + docstrings + type hints.

## Modules (config-driven; no llm/mcp/pygame/network imports — grep-verified)
`board.py` (in_bounds, is_blocked, 8-dir king-move neighbors, no corner-cutting) ·
`moves.py` (legal_moves, apply_move, cop-only `place_barrier` impassable to both) ·
`rules.py` (capture, survival, turn order, config scoring) · `match.py` (SubGame loop,
Game with Technical-Loss void+rerun) · `state.py` (serializable, byte-stable GameState).

## Verification (independently re-run)
- ruff `All checks passed!`; ruff format clean; line-cap OK (≤150).
- `pytest -m 'not live'` → **109 passed, 99.09%** overall (gate 85%).
- `game/` package coverage = **100%** (gate 90%).
- No `genai/gemini/fastmcp/mcp/pygame/network` imports anywhere under `game/`.
