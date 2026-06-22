# Prompt log — Phase 0 (repo bootstrap)

**Phase goal:** repo skeleton, tooling, `CLAUDE.md`, local `git init` + first commits — no business
logic. The grade is the ORCHESTRATION, not the game strategy. Tooling ported from
`~/COSMOS77/HW5/COSMOS77-ex05/`; package renamed `cosmos77_ex05` -> `cosmos77_ex06`, exercise 5 -> 6.

## What was built

1. **Layout** — `src/cosmos77_ex06/` with `__init__.py` + `constants.py`, the `sdk/`, `shared/`,
   and `cli/` packages filled, and empty (but importable) `game/`, `agents/`, `mcp_servers/`,
   `orchestrator/`, `strategy/`, `gui/`, `deploy/`, `report/`, `bonus/` subpackages.
   `tests/{unit,integration}`, `docs/prompts/`, `config/`, `assets/`, `reports/`, `scripts/`.
2. **pyproject.toml** — project `cosmos77-ex06` v1.00, Python `>=3.11,<3.12`, hatchling, wheel
   `["src/cosmos77_ex06"]`, the `cosmos77-pursuit` script. Deps: fastmcp, google-genai, pyyaml,
   pydantic, rich, pygame, matplotlib, numpy, the Google API client stack, python-dotenv. Dev:
   pytest(+cov/mock/asyncio), ruff, hypothesis, pre-commit. ruff line-length 100 / py311 /
   E,F,W,I,N,UP,B,C4,SIM (ignore E501); pytest `asyncio_mode = "auto"` + a `live` marker; coverage
   branch + `fail_under = 85`.
3. **config/config.yaml** — grid 5x5, 25 moves, 6 sub-games, 5 barriers, the scoring table, turn
   order thief->cop, diagonal on, the Gemini model, the two MCP URLs+ports, the report target,
   group metadata, output paths (no hardcoding; spec §10).
4. **shared/** — `version.py` (VERSION 1.00 + validation), `config.py` (YAML loader, dot-path get,
   `.env` secrets, version check), `logging_setup.py` (`cosmos77_ex06` namespace), `gatekeeper.py`
   (LLM meter + result ledger + secret scrub). `sdk/sdk.py` skeleton (stages raise
   `NotImplementedError`). `cli/main.py` thin `--version` + run/report/bonus dispatcher.
5. **Tooling** — `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.gitignore`, `.env.example`,
   `.python-version`, `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CLAUDE.md`.
6. **Tests** — `conftest.py` (seed 1729 + tmp config fixtures) and unit tests for config, version,
   gatekeeper, logging_setup, the CLI `--version`, and the SDK skeleton — ≥85% coverage.

## Gates driven green
`uv sync`; `uv run ruff check .`; `uv run ruff format --check .`;
`uv run python scripts/check_line_cap.py`; `uv run pytest -m "not live"` (coverage gate);
`uv run pre-commit run --all-files`.
