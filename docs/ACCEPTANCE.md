# ACCEPTANCE.md — HW6 acceptance audit (Phase 12)

Maps every acceptance criterion (**E1–E13**, playbook §1.5) and the **17 global rules**
(playbook §1 / `CLAUDE.md`) to the file(s)/test(s)/artifact that satisfy it, with an honest status.

**Status legend**

- **DONE (CI-proven)** — code + tests + GitHub CI green (clean checkout → `uv sync --frozen` → ruff
  → line-cap → `pytest -m "not live" --cov-fail-under=85`).
- **DONE (live-validated)** — already exercised against real Gemini (verified small-rung games with
  genuine bluffing transcripts; see README §6/§7).
- **READY — awaits live touchpoint** — code-complete and mocked-tested, but the final real artifact
  needs a one-time human/quota step (free-tier quota, Gmail OAuth, cloud deploy, or a partner group).

The full Phase-12 gauntlet (ruff check, `ruff format --check`, line-cap, `pytest -m "not live"
--cov-fail-under=85`, E3 grep, secrets check, `uv lock --check`, frozen reproducibility) passed
locally **and** on GitHub CI (latest push green). Total coverage **98.73%**; graded modules
(`game/`, `shared/config`, `report/`) **100%**.

---

## E1–E13 acceptance criteria

| ID | Criterion | Satisfied by (code) | Tests / artifacts | Status |
|----|-----------|---------------------|-------------------|--------|
| **E1** | Config-driven grid: diagonal moves, cop-only barriers (≤5), capture detection, turn order (thief→cop), 25 moves/sub-game, 6 sub-games, scoring table | `game/board.py`, `game/moves.py`, `game/rules.py`, `game/match.py`, `game/state.py` | `tests/unit/test_game/*` (board, moves, rules, match, meta_rules, state, game_runner, sdk_game) — `game/` at **100%** | **DONE (CI-proven)** |
| **E2** | Two separate FastMCP servers (cop + thief), tools only, each with revocable token auth | `mcp_servers/cop_server.py`, `thief_server.py`, `server.py`, `tools.py`, `auth.py` (`StaticTokenVerifier`, env tokens, rotation = revocation) | `tests/unit/test_mcp/*` (test_tools, test_no_llm, test_module_and_live); `auth.py`, `tools.py` at **100%** | **DONE (CI-proven)** |
| **E3** | Server/Client separation — the LLM lives in the orchestrator, **never** inside `mcp_servers/` | LLM only in `orchestrator/gemini_client.py` + `agents/`; `mcp_servers/` exposes tools only | `grep -rnE 'genai|gemini|openai|anthropic' src/cosmos77_ex06/mcp_servers/` → **empty**; `tests/unit/test_mcp/test_no_llm.py` asserts no forbidden imports; `tests/unit/test_orchestrator/test_engine_e3e4.py` asserts the engine (not the server) drives Gemini | **DONE (CI-proven)** + **DONE (live-validated)** (real games ran with the LLM in the client) |
| **E4** | Free natural-language communication under partial observability; agents infer opponent position from text (no rigid numeric protocol) | `agents/base.py` (prompt forbids raw coordinates/rows/cols), `agents/belief.py` (text → position estimate), `orchestrator/guard.py` (`CoordinateGuard`, config-driven `nl_guard.coord_patterns`) | `tests/unit/test_orchestrator/test_guard.py` (flags coord-shaped, passes prose), `test_agents.py` (prompt forbids coords), `test_engine_e3e4.py` (coord leak flagged in transcript); **real transcript** in README §6 (thief bluff + cop seeing through it) | **DONE (CI-proven)** + **DONE (live-validated)** |
| **E5** | Fully autonomous pipeline: init → 6 valid sub-games → automated report, zero manual intervention | `orchestrator/runner.py` (`run_full_game`), `sdk/sdk.py`, `cli/main.py` (`run`), cop auto-emails via `report/dispatch.auto_send` | `tests/unit/test_game/test_game_runner.py`, `test_orchestrator/*`, `test_report/test_dispatch.py` (mocked agents → 6 valid sub-games + auto-send) | **READY — awaits live touchpoint** (headline 6-game live run; gated by `gemini-2.5-flash` free tier = 20 req/day). Pipeline is identical to the verified live 2×2/3×3 runs — only `num_games`/`grid_size` change in config |
| **E6** | Local → cloud: proven on localhost (separate ports), then public HTTPS URLs (Horizon/tunnel) with token auth | `orchestrator/cloud.py` (HTTPS guard, `run_cloud_game`), `--cloud` flag, `deploy/horizon.md`, `deploy/tunnel.sh`, config `mcp.cop_url/thief_url` | `tests/unit/test_deploy/*` (cloud build, cross-process state sync, HTTPS guard) — all mocked, no network in CI | **READY — awaits live touchpoint** (deploy to Horizon **or** `cloudflared`; config URLs are still `localhost`. Local two-port run is proven) |
| **E7** | Automated Gmail JSON report — cop auto-sends ONE email (JSON body only) to `rmisegal+uoh26b@gmail.com` at game end | `report/gmail_sender.py` (OAuth desktop, JSON-only body, base64url, `userId="me"`), `report/dispatch.py`, `report/builder`/`output.py`, `report/schema.py` (pydantic), config `report.to` | `tests/unit/test_report/*` (mocked `googleapiclient`; JSON-only body; `messages().send`; token refresh) — `report/` at **100%** | **READY — awaits live touchpoint** (real send needs one-time Gmail OAuth: `credentials.json` + consent screen, `cosmos77-pursuit report --send`) |
| **E8** | Config file, no hardcoding (grid, moves, games, barriers, scoring, ports, URLs, model) | `config/config.yaml`, `shared/config.py` (`Config` loader + version check) | `shared/config.py` at **100%**; consumed everywhere (board, rules, match, guard, mcp, report) | **DONE (CI-proven)** |
| **E9** | Decision mechanism (heuristic and/or Q-Table) | `strategy/heuristic.py` (Manhattan/Chebyshev on the *estimate*), `strategy/qtable.py` (Bellman + ε-greedy), `strategy/plots.py` | `tests/unit/test_strategy/*` (heuristic reduces distance, Bellman update matches, ε-greedy explore/exploit); `assets/learning_curve.png` (offline RL self-play) | **DONE (CI-proven)** |
| **E10** | GUI showing the game in real time + CLI logs proving valid MCP comms | `gui/viewer.py`, `render.py`, `theme.py`, `driver.py` (headless-safe); structured per-turn logs via `orchestrator/turn_log.py` + `logging_setup.py` (`show_server_url: true`) | `tests/unit/test_gui/*` (render draw-calls, turn-log format incl. MCP URL + NL message); committed frames `assets/gui_start.png`, `gui_midgame.png`, `gui_capture.png` | **DONE (CI-proven)** for GUI render + log format & screenshots. **READY — awaits live touchpoint** for the *cloud*-MCP CLI log capture (gated by the cloud deploy in E6) |
| **E11** | Scientific README: Dec-POMDP formal model + tuple ⟨n,S,{Aᵢ},P,R,{Ωᵢ},O,γ⟩, orchestration analysis, learning curves, screenshots, CLI logs | `README.md` (§2 formal model, §3 architecture, §4 orchestration challenge, §6 NL protocol, §7 results, §8 visuals) | `README.md` ≈ 34 KB, 5+ embedded images; `docs/PRD_dec_pomdp.md` | **DONE (CI-proven)** (README content) |
| **E12** | Inter-group BONUS (ready-to-activate): role-swap series, matching `bonus_game` JSON with `mutual_agreement` | `bonus/series.py`, `bonus/report.py`, `bonus/schema.py`, `bonus/diff_check.py`, `bonus/cloud.py`, `bonus/run.py`, `bonus/coordinate.md` | `tests/unit/test_bonus/*` (role assignment, schema-valid JSON, deterministic canonical serializer, bonus_claim win/lose/tie); `reports/bonus_game.sample.json` | **READY — awaits live touchpoint** (needs a partner group; harness is code-complete + tested) |
| **E13** | Technical-Loss handling — failed sub-games voided + re-run to complete 6 valid sub-games | `orchestrator/runner.py` (`_is_void`, void-and-rerun loop; `game/match.py` `TechnicalLoss`) | `tests/unit/test_game/*` + `test_orchestrator/*` (a Technical-Loss triggers a rerun; a void never consumes a slot) | **DONE (CI-proven)** |

### E1–E13 status summary

- **DONE (CI-proven):** E1, E2, E3, E4, E8, E9, E11, E13 — **8** (E3 & E4 also **live-validated**).
- **READY — awaits live touchpoint:** E5, E6, E7, E12 — **4**, plus the cloud-CLI-log half of **E10**.
- **Net:** 8 fully DONE, 1 split (E10: GUI/log DONE, cloud-log READY), 4 READY-awaits-touchpoint.

Every READY item is **code-complete and mocked-tested**; only the final real-world artifact (free-tier
quota run, Gmail OAuth, cloud deploy, or partner group) remains — none requires further code.

---

## The 17 global rules

| # | Rule | Evidence | Status |
|---|------|----------|--------|
| 1 | 150-line hard cap per `.py` | `scripts/check_line_cap.py` OK; `find src tests scripts -name '*.py' | xargs wc -l | awk '$1>150'` → empty (largest files exactly 150) | **DONE** |
| 2 | SDK architecture — business logic via `class SDK` | `sdk/sdk.py`; CLI/GUI/orchestrator call the SDK | **DONE** |
| 3 | OOP, no duplication (shared module / base class) | `agents/base.py` → Cop/Thief; `mcp_servers/server.py` shared; `mcp_servers/auth.py` shared verifier | **DONE** |
| 4 | Zero hardcoded config | `config/config.yaml` + `shared/config.py`; grid/moves/games/barriers/scoring/ports/URLs/model/guard-patterns all in config | **DONE** |
| 5 | `uv` is the only package manager | `pyproject.toml` + `uv.lock`; CI `uv sync --frozen`; `uv lock --check` passes | **DONE** |
| 6 | TDD; mock ALL LLM/MCP/network/Gmail/GUI; no live calls in suite | 330 passed / 2 deselected (`live`-marked); no real `genai.Client`/http/socket/Gmail in tests | **DONE** |
| 7 | Coverage ≥ 85% on game + config + report | game/ 100%, shared/config 100%, report/ 100%; total 98.73% | **DONE** |
| 8 | `ruff check` zero violations | `uv run ruff check .` → All checks passed; `ruff format --check` clean | **DONE** |
| 9 | No secrets in repo | `git ls-files | grep -iE '.env|credential|token'` → only `.env.example`; `.gitignore` covers `.env`/`credentials.json`/`token.json`/`*.token`; `detect-private-key` pre-commit Passed | **DONE** |
| 10 | Versioning starts at 1.00 | `pyproject.toml` `version = "1.00"`; `shared/version.py` `VERSION="1.00"` + config-version validation | **DONE** |
| 11 | Conventional Commits per task | 68 commits, conventional prefixes (`feat`/`test`/`docs`/`chore`), 0 wip/tmp/fixup | **DONE** |
| 12 | Prompt log per session | `docs/prompts/000`–`012` (this phase adds `012_phase12_qa.md`) | **DONE** |
| 13 | Gatekeeper meters every LLM call | `shared/gatekeeper.py`; routed via `orchestrator/gemini_client.py` (+ cloud/local/runner) | **DONE** |
| 14 | CLI only; real code + real autonomous run | `cosmos77-pursuit` entry point; live small-rung games verified (README §7) | **DONE** (headline 6-game live run is READY — awaits free-tier quota) |
| 15 | Docstrings on every public class/function/module | Module + public-symbol docstrings throughout `src/` | **DONE** |
| 16 | Type hints on every public signature | `from __future__ import annotations`; no return-annotation-less `def` in `src/` | **DONE** |
| 17 | Deterministic tests (seed, fixed prompts, mocked I/O) | scripted fake Gemini clients, fixed positions, seeded RL; no flakes across repeated runs | **DONE** |

All 17 rules satisfied. Rule 14's only outstanding piece is the headline 6-sub-game live run, which is
quota-gated (not a code gap).

---

## Gaps (adversarial self-audit)

1. **Single-author git history (expectation gap).** All **68** commits are authored by
   `Abdallah Khaldi <abdallahkh12@icloud.com>`. The playbook §14 step 8 expects "both authors";
   **Tasneem Natour has no commits.** This is a real gap against the stated expectation. History is
   **not** rewritten (out of scope for Phase 12, and rewriting authorship would be dishonest). If
   co-authorship is required, the cleanest remedy is a co-authored commit going forward and/or a note
   on the cover sheet; alternatively add `Co-authored-by:` trailers on future commits.
2. **E5 / E7 not yet exercised end-to-end live.** The autonomous 6-sub-game run + the real Gmail
   send are quota- and OAuth-gated, not code-gated. Code-complete and mocked-tested; the live artifact
   awaits a human touchpoint (free-tier 20 req/day; one-time `credentials.json` + consent).
3. **E6 / E10 (cloud half) not yet deployed.** `config.yaml` still points `mcp.*_url` at
   `localhost`; the public Horizon/tunnel URLs and the cloud-MCP CLI-log capture await a deploy step.
   The `--cloud` path, HTTPS guard, and deploy docs are complete and tested.
4. **E12 awaits a partner group.** Harness, schema, canonical serializer, and diff-check are
   code-complete and tested; activation needs a second group to exchange URLs + matching JSON.
5. **`mcp_servers/app.py` 0% coverage (minor).** The ASGI entry (`mcp.http_app()`) is a 3-line
   deployment shim, untested by design (no network in CI). Does not affect the graded-module floor.

None of gaps 2–5 is a code deficiency — each is a single real-world touchpoint. Gap 1 is the only
true expectation mismatch.

---

## Pre-submission checklist (remaining human actions)

- [ ] **Live 6-sub-game run (E5).** With `GEMINI_API_KEY` set, run `cosmos77-pursuit run --games 6`
      (mind the free-tier 20 req/day on `gemini-2.5-flash`; Technical-Loss reruns absorb transient 429s).
- [ ] **Gmail OAuth + real send (E7).** Place `credentials.json` (Google Cloud OAuth desktop client,
      `gmail.send` scope, yourself as Test user), then `cosmos77-pursuit report --send` (first run opens
      the consent screen, writes `token.json`, emails the JSON to `rmisegal+uoh26b@gmail.com`).
- [ ] **Cloud deploy (E6/E10).** Deploy both servers to Prefect Horizon **or** `cloudflared tunnel`,
      put the two public HTTPS URLs in `config.yaml` (`mcp.cop_url/thief_url`), and run
      `cosmos77-pursuit run --cloud --games 1` to capture the cloud-MCP CLI logs for the README.
- [ ] **Bonus (E12, optional).** Secure a partner group; exchange the four MCP URLs + a shared token;
      run the role-swap series; both groups email the byte-identical `bonus_game` JSON (use the shared
      canonical serializer + `bonus/diff_check.py` before sending; mismatch → 0 for both).
- [ ] **Co-authorship (gap 1).** If "both authors" is required, add `Co-authored-by: Tasneem Natour`
      trailers going forward (do **not** rewrite history).
- [ ] **Cover PDF (Phase 13).** Generate `COSMOS77-ex06.pdf` (exercise = 6), tag `v1.00`, release.
- [ ] **Moodle upload.** **Both** students (Abdallah Khaldi + Tasneem Natour) upload the cover PDF
      separately. Confirm the repo is public (or add `rmisegal@gmail.com` as collaborator).
