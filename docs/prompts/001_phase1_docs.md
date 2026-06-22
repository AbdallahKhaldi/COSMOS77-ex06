# Prompt log — Phase 1: Mandatory documentation

**Goal.** Author every mandatory document before any business logic: the master PRD, ten
per-mechanism PRDs, the PLAN (architecture + ADRs + risk register), and the granular TODO
backlog (≥600 tasks). Per playbook §3 and CLAUDE.md.

## Approach
Phase 1 was executed as a **parallel fan-out**: 13 independent authoring agents, one per
document, each grounded in the same context (playbook §1/§1.5/§3, `CLAUDE.md`,
`config/config.yaml`, and the project memory files) and instructed to keep the central thesis
front-and-centre — *the grade is the orchestration, not the game strategy* — and to use the
spec vocabulary (Dec-POMDP, partial observability, MCP Server/Client separation, FastMCP,
free natural language, token auth, Technical-Loss). Each agent wrote exactly one file; no agent
touched git or another file. Results were then verified against the acceptance gates below.

## Deliverables
- `docs/PRD.md` — master PRD: context, research questions RQ1–RQ7, functional requirements
  FR-1..FR-13 mapped 1:1 to acceptance E1–E13, NFRs, KPIs, full traceability matrix.
- 10 mechanism PRDs: `PRD_game`, `PRD_mcp_servers`, `PRD_orchestrator`, `PRD_nl_protocol`,
  `PRD_strategy`, `PRD_gui`, `PRD_deploy`, `PRD_report`, `PRD_bonus`, `PRD_dec_pomdp`.
- `docs/PLAN.md` — C4 description, one-turn sequence diagram, ADR-001..ADR-007, risk register.
- `docs/TODO.md` — 646 tasks (`T-0001`..`T-0646`) across phases P0–P13, no duplicate ids.

## Decisions surfaced during authoring
- Added a `vision_radius` tunable to `config/config.yaml` (default 1): the partial-observability
  window the MCP servers expose. It realizes the Dec-POMDP observation function `O` and keeps the
  opponent's exact cell hidden, forcing natural-language inference. Config-driven (no hardcoding).
- Deployment is documented **platform-agnostic** (matching the spec's "Prefect Cloud or a similar
  platform" + tunnels): Cloudflare Tunnel as the simple default (cloudflared is installed),
  Prefect Horizon / FastMCP Cloud as the hosted option with stable URLs.

## Verification (all green)
- `ls docs/PRD_*.md | wc -l` → 10
- `grep -c '^T-' docs/TODO.md` → 646 (≥600)
- `grep -c 'ADR-' docs/PLAN.md` → 26 references (ADR-001..007)
- Dec-POMDP tuple ⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩ present in `PRD_dec_pomdp.md`.
