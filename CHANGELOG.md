# Changelog

All notable changes to COSMOS77-ex06 are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses a single
course-mandated version line starting at **1.00** (CLAUDE.md rule 10).

## [1.00] — 2026-06-22

### Added (Phase 0 — repo bootstrap)
- Repository scaffold: the `src/cosmos77_ex06/` package skeleton (constants + the
  `cosmos77-pursuit` CLI entry point + the SDK + empty `game/`, `agents/`,
  `mcp_servers/`, `orchestrator/`, `strategy/`, `gui/`, `deploy/`, `report/`,
  `bonus/` subpackages), `tests/{unit,integration}`, `docs/prompts/`, `config/`,
  `assets/`, `reports/`, and `scripts/`.
- Tooling ported from `COSMOS77-ex05`: `pyproject.toml` (project `cosmos77-ex06`
  v1.00, Python `>=3.11,<3.12`, the FastMCP / google-genai / pygame / matplotlib /
  Gmail-API runtime deps, a dev group with pytest-asyncio + ruff + pre-commit,
  ruff/coverage-85/pytest config with `asyncio_mode = "auto"`),
  `.pre-commit-config.yaml`, `.github/workflows/ci.yml`,
  `scripts/check_line_cap.py`, `scripts/generate_cover_pdf.py` (retargeted to
  ex06 / exercise 6).
- Configuration: `config/config.yaml` (grid/moves/games/barriers/scoring,
  turn order, diagonal, the Gemini model, the two MCP URLs+ports, the report
  target, group metadata, output paths — no hardcoding, spec §10),
  `config/logging_config.json`. `.env.example` (GEMINI_API_KEY + the three MCP
  tokens; no secrets).
- Shared modules: `version.py` (VERSION 1.00 + config-version validation),
  `config.py` (YAML loader with dot-path access + `.env` secrets),
  `logging_setup.py` (the `cosmos77_ex06` log namespace), `gatekeeper.py` (the
  LLM meter + result ledger with secret scrubbing).
- Governance: `CLAUDE.md` (the 17 binding rules + the E1–E13 pointer + HW6
  vocabulary), `CONTRIBUTING.md`, `LICENSE` (MIT 2026, both authors), `README.md`
  (placeholder — becomes the Dec-POMDP report in Phase 10).
- Quality gates green: `uv sync`, `ruff check`, `ruff format --check`,
  `check_line_cap.py`, `pytest` (≥85% coverage), and `pre-commit run --all-files`.

[1.00]: https://github.com/AbdallahKhaldi/COSMOS77-ex06/releases/tag/v1.00
