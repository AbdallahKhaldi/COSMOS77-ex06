# COSMOS77-ex06 — Cops & Robbers: Dual AI Agents over MCP

> **Placeholder.** This README becomes the scientific Dec-POMDP report in Phase 10.

HW6 for **Orchestration of AI Agents (203.3763)**, Dr. Yoram Segal (UOH). Two
autonomous AI agents — a **Cop** and a **Thief** — play a config-driven
Cops & Robbers pursuit on a grid, each backed by its own **FastMCP server**,
coordinating in **free natural language** under partial observability, driven by
an **orchestrator (MCP Client) running Gemini** with native MCP tool-calling.
Local first, then deployed to public cloud HTTPS URLs, ending with an
**automated Gmail JSON report**. The grade is the **orchestration**, not the game
strategy.

## Authors

- Abdallah Khaldi (212389712)
- Tasneem Natour (323118794)

## Quick start

```bash
uv sync
cp .env.example .env   # add GEMINI_API_KEY + the three MCP tokens
uv run cosmos77-pursuit --version
```

See `CLAUDE.md` for the 17 binding rules and `../CLAUDE_CODE_PLAYBOOK.md` for the
full phase plan and the E1–E13 acceptance criteria.
