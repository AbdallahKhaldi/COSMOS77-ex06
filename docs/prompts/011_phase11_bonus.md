# Phase 11 — Inter-group BONUS harness (ready-to-activate) (E12)

## Goal
Build the inter-group bonus competition harness **ready-to-activate** (spec §12,
`docs/PRD_bonus.md`): the moment a partner group is secured, the role-swap series
runs over four public cloud MCP URLs and **both groups email a byte-identical
`bonus_game` JSON**. A mismatch → **0 for both**, so determinism is the whole game.
Everything is MOCKED in tests (no live cloud / MCP / LLM / Gmail). The orchestrator,
mcp_servers, and game packages were **not** touched — the bonus reuses them as a library.

## What was built (`src/cosmos77_ex06/bonus/`)
- **`series.py`** (150) — `run_series(config, gatekeeper, *, client_factory, engine_factory)`
  drives the symmetric **role-swap** over the four cloud URLs:
  - sub-games **1-3**: OUR (`group_1`) cop server vs THEIR (`group_2`) thief server;
  - sub-games **4-6**: THEIR (`group_2`) cop vs OUR (`group_1`) thief.
  `role_map(index)` returns the cop/thief slot per sub-game; each sub-game is delegated
  to the existing `GameEngine` (no loop re-implementation). Technical-Losses against a
  foreign server are **voided + re-run** until 6 valid sub-games exist (E13). The engine
  factory is resolved at call time so it is injectable/monkeypatchable — tests do zero
  live calls. `run_series_sync` is the synchronous wrapper for the SDK/CLI.
- **`cloud.py`** (49) — `build_cloud_engine(...)` opens a token-authed `fastmcp.Client`
  per public HTTPS URL (shared `BONUS_MCP_TOKEN` from `.env`, Rule 9) and reuses
  `GameEngine` (Server/Client separation, E3, preserved across the group boundary). No
  network at import; fully bypassed in tests via the injected `engine_factory`.
- **`schema.py`** (97) — pydantic v2 `BonusGameReport` (`extra='forbid'`) pinning the
  EXACT §9.2 key set; a model validator rejects totals/claim key drift and any
  totals-vs-sub-game-sum mismatch.
- **`report.py`** (122) — `build_report` assembles + validates the §9.2 dict from the
  `bonus` config block; `totals_by_group` maps each sub-game's `group_1`/`group_2` slot
  to the agreed group CODE and sums; `bonus_claim` resolves win 10 / lose 7 / tie 5 from
  config thresholds. **`serialize` delegates to the SAME canonical serializer as the
  single-group report** (`report/output.canonical_json`: `sort_keys=True`,
  `ensure_ascii=False`, `indent=2`) so both groups emit byte-identical bytes.
- **`run.py`** (47) — high-level driver (kept out of `sdk.py` for the 150-line cap):
  run the series → build → validate → serialize → optionally write `reports/bonus_game.json`
  → record totals on the gatekeeper.
- **`diff_check.py`** (63) — the pre-send byte-for-byte comparator (PRD §8): `IDENTICAL`
  vs `MISMATCH at byte K` plus a key-by-key localization of the offending field.
- **`coordinate.md`** — the partner checklist (orientation, four URLs + shared token,
  identical game config, run, **diff before send**, `mutual_agreement: true`, both email
  before 08:30 Friday) with a `diff -q` snippet + the Python diff helper.

## Wiring
- **`config/config.yaml`** — a `bonus:` block (commented/placeholder, `enabled: false`):
  the four MCP URLs, group_2 code/repo/students, `engine_runner`, and `claim` thresholds.
  `.env.example` gained `BONUS_MCP_TOKEN` (the shared revocable cross-group token).
- **`SDK.bonus(...)`** delegates to `bonus.run.run_bonus`.
- **CLI** `cosmos77-pursuit bonus --partner <config>` runs the series (stub-safe; the real
  run needs the partner touchpoint — placeholder URLs void out until filled).

## The `bonus_game` top-level keys (byte-for-byte, §9.2)
`report_type`, `groups` {group_1, group_2}, `github_repo_group_1`, `github_repo_group_2`,
`mcp_url_group_1_cop`, `mcp_url_group_1_thief`, `mcp_url_group_2_cop`, `mcp_url_group_2_thief`,
`timezone`, `students_group_1`, `students_group_2`, `sub_games`, `totals_by_group`,
`bonus_claim`, `mutual_agreement`. Determinism is **asserted** (two builds byte-equal; a
shuffled-key dict serializes to the same bytes; Hebrew names stay raw UTF-8, not `\uXXXX`).

## Tests (`tests/unit/test_bonus/`, all mocked + deterministic — Rule 6/17)
- `test_series.py` — the role swap (1-3 our-cop/their-thief, 4-6 their-cop/our-thief), the
  four-URL wiring per sub-game, capture/survival mapping, Technical-Loss void+rerun, give-up.
- `test_report.py` — exact §9.2 keys, schema validity, `totals_by_group`, `bonus_claim`
  win/lose/tie, **byte-identical determinism** + insertion-order independence + raw-Unicode.
- `test_diff_check.py` — identical vs mismatch (offset + key localization).
- `test_cloud_and_run.py` — the cloud factory wiring; `run_bonus`/`SDK.bonus` end-to-end
  (engine factory monkeypatched); two independent runs ("both groups") emit identical bytes.

## Gates
`ruff check .` clean; `ruff format --check` clean; `check_line_cap` clean (every file ≤150);
`pytest -q -m 'not live'` → **299 passed**, total coverage **98.74%** (bonus package ~100%).
A canonical `reports/bonus_game.sample.json` is committed.

## Activation (human touchpoint — not code)
Secure a partner, fill the `bonus` block + `BONUS_MCP_TOKEN`, deploy/confirm the four cloud
URLs, run `bonus --partner config/`, run the diff, set `mutual_agreement: true`, and **both
groups email the byte-identical `bonus_game` JSON before 08:30** on the bonus Friday.
