# CLAUDE.md — Project rules of engagement (binding for every prompt)

HW6 (Dual AI-agent Cops & Robbers via MCP) for Dr. Yoram Segal's Orchestration of AI Agents
(203.3763) course. Every prompt inherits these rules. HW6 acceptance criteria (E1–E13) are in
../CLAUDE_CODE_PLAYBOOK.md §1.5. The grade is the ORCHESTRATION, not the game strategy.

## The 17 rules
1. 150-line hard cap per .py file. Split it.
2. SDK architecture: all business logic via class SDK in src/cosmos77_ex06/sdk/sdk.py.
3. OOP, no duplication. 2 files -> shared module; 3 -> base class/mixin (BaseAgent).
4. Zero hardcoded config (grid, moves, games, barriers, scoring, ports, URLs, model) -> config/config.yaml.
5. uv only.
6. TDD red->green->refactor. Mock ALL LLM/MCP/network/Gmail/GUI I/O. No live calls in the suite.
7. Coverage >= 85% on game logic + config + report.
8. ruff check returns zero violations.
9. No secrets in repo. .env.example only; GEMINI_API_KEY, MCP tokens, credentials.json/token.json gitignored.
10. Versioning starts at 1.00.
11. Conventional Commits per task; reference TODO IDs.
12. Prompt log: every session -> docs/prompts/NNN_*.md.
13. Gatekeeper: every LLM call routes through shared/gatekeeper.py (short calls; measured).
14. CLI only (Claude Code terminal). The deliverable is real code + a real autonomous game run.
15. Docstrings on every public class/function/module.
16. Type hints on every public signature.
17. Deterministic tests. Seed random; fix prompts/positions; mock all I/O. No flakes.

## Architecture rule (graded)
The LLM lives ONLY in the orchestrator (MCP Client). The FastMCP servers expose TOOLS ONLY — never
import or call an LLM inside mcp_servers/. Agents communicate in FREE natural language, never a rigid
numeric protocol. The game is formally a Dec-POMDP with partial observability.

## Language & vocabulary
English. Use: Dec-POMDP, partial observability, MCP Server/Client separation, FastMCP, free natural
language, orchestration, token auth, Prefect Horizon (not "Prefect Cloud").

## When in doubt
Less code, fewer deps, clearer docstrings. Impossible rule -> ADR in docs/PLAN.md. A fully autonomous
pipeline talking natural language over cloud MCP servers outranks any clever game strategy.
