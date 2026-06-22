# Phase 7 — Full autonomous local runner + rate-limit hardening (E5, E13)

## Goal
A fully autonomous full game: from `init` to a saved internal-game report with **zero
manual intervention** (E5). A sub-game that fails technically is **voided and re-run**
until exactly `num_games` valid sub-games exist (Technical-Loss, E13). Plus rate-limit
hardening for the real free-tier run (hundreds of Gemini calls).

## What was built
- **`src/cosmos77_ex06/orchestrator/runner.py`** — `run_full_game(config, gatekeeper,
  client_factory, *, gui)` opens the in-memory cop/thief FastMCP clients once, drives the
  `GameEngine` per sub-game, catches any `TechnicalLoss`/transport exception (and any
  result flagged `technical_loss`), records a transcript void note, increments `reruns`,
  and re-runs — a voided attempt never consumes a 1-based index nor scores. After exactly
  `num_games` valid sub-games it assembles the §9.1 report dict via `build_report`. If the
  rerun budget is exhausted it raises `TechnicalLoss` (never emits a short report).
- **`src/cosmos77_ex06/report/schema.py`** — pydantic v2 `InternalGameReport` with
  `extra="forbid"` pinning the EXACT top-level keys: `group_name`, `students`,
  `github_repo`, `cop_mcp_url`, `thief_mcp_url`, `timezone`, `sub_games`, `totals`.
  A model validator rejects any report whose `totals` ≠ the per-sub-game sums.
  `sub_games[]` entries are `{sub_game, winner, moves, cop_score, thief_score}`.
- **`src/cosmos77_ex06/report/output.py`** — canonical JSON writer (`sort_keys`, UTF-8,
  indent 2), `save_report`, `save_transcript`, and the `run_sanity_ladder` driver
  (2x2 → 3x3 → 4x4 → 5x5, one transcript per rung, grid restored afterwards). Split out
  so `sdk.py` stays under the 150-line cap.
- **`SDK.run_full_game(...)`** — runs the full game, validates the report against the
  schema, saves it to `reports/internal_game.json` (canonical), records the totals on the
  gatekeeper, returns `{report, transcript}`. **`SDK.run_sanity_ladder(...)`** drives the
  ladder. CLI `run --local --games 6` produces the report; `run --ladder` runs the ladder.

## Rate-limit hardening
- **`src/cosmos77_ex06/orchestrator/llm_retry.py`** (extracted so both it and
  `gemini_client.py` stay ≤150) holds `RetryPolicy`:
  - `is_transient` — 429 / RESOURCE_EXHAUSTED / 5xx detection.
  - `parse_retry_delay` — reads the server's `RetryInfo.retryDelay`, both the structured
    `exc.retry_delay.seconds` form and the string `'retryDelay': '7s'` embedded in the
    google-genai error. The policy **waits exactly that delay** instead of guessing;
    only when the server suggests nothing does it fall back to exponential backoff
    (`retry_base_seconds * 2**attempt`).
  - optional inter-call **pacing** via `llm.min_call_interval_seconds` (default 0 —
    behaviour identical to before when unset and when no 429 occurs).
- `gemini_client.py` now builds a `RetryPolicy` from config and wraps the async
  `generate_content` call through `policy.run(...)`.

## Config additions (`config/config.yaml`)
- `llm.min_call_interval_seconds: 0.0` — inter-call pacing seconds (0 disables).
- `students: [{name, id}, ...]` — the §9.1 roster.

## Tests (mocked agents/Gemini/MCP — no live calls)
- `tests/unit/test_report/test_schema.py` — exact §9.1 keys, totals match, enum + extra-key
  rejection.
- `tests/unit/test_orchestrator/test_runner.py` — exactly `num_games` valid sub-games;
  a Technical-Loss is voided + re-run to still reach `num_games`; the report validates;
  totals equal the sub-game sums; exhausting reruns raises.
- `tests/unit/test_orchestrator/test_llm_retry.py` — retry waits per `retryDelay` (near-zero
  delay) then succeeds; backoff fallback; non-transient not retried; pacing.
- `tests/unit/test_sdk.py` — `run_full_game` validates + saves; `run_sanity_ladder` writes a
  transcript per rung and restores the grid.

## Verification (live — run separately by the parent)
```bash
uv run cosmos77-pursuit run --local --games 6
test -f reports/internal_game.json
```

A mocked sample `reports/internal_game.json` is committed so the schema is visible.
