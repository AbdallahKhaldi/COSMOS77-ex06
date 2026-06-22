# Contributing to COSMOS77-ex06

Working agreement for the two student contributors (Abdallah Khaldi and Tasneem
Natour) and any future maintainers. Mirrors the 17 binding rules in
[CLAUDE.md](CLAUDE.md) and the master playbook (`../CLAUDE_CODE_PLAYBOOK.md`).

## Local setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # one-time
uv sync
uv run pre-commit install
cp .env.example .env   # add GEMINI_API_KEY + the three MCP tokens
```

`uv sync` materialises `.venv/` and `uv.lock`. **Never** invoke `pip`,
`python -m venv`, or `python script.py` directly for OUR code (rule 5).

## Architecture (graded)

The LLM lives **only** in the orchestrator (the MCP Client). The two FastMCP
servers expose **tools only** — never import or call an LLM inside
`src/cosmos77_ex06/mcp_servers/`. Agents communicate in **free natural
language**, never a rigid numeric protocol. The pursuit is formally a Dec-POMDP
under partial observability. All business logic flows through `class SDK` (rule 2).

## Commits

Conventional Commits (rule 11): `type(scope): summary` + a body referencing the
TODO ID (`Closes T-NNNN`). Multiple commits per phase; no `wip`/`tmp`/`fixup`.
Two-person team — work is authored by both partners across the history.

## Quality gates (run before pushing)

```bash
uv run ruff check .                 # zero issues
uv run ruff format --check .        # zero diffs
uv run python scripts/check_line_cap.py
uv run pytest -m "not live" --cov-fail-under=85
```

The same gates run in [GitHub Actions](.github/workflows/ci.yml) on every push.
Live runs (real Gemini / MCP / Gmail / GUI) are marked `live` and excluded from
CI — the suite mocks **all** LLM, MCP, network, Gmail, and GUI I/O (rule 6).

## Honesty

Game results and the JSON report flow through the **result ledger**
(`results/*.json` via the Gatekeeper) — the single source of truth (rule 13).
The bonus report uses a **shared canonical serializer** so both groups emit a
byte-identical JSON (a mismatch scores 0 for both). If a rule genuinely cannot be
followed for a module, document the exception as an ADR in `docs/PLAN.md`.
