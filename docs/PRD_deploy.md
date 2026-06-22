# PRD — Deployment: Local → Cloud (E6)

> **Scope.** This document specifies how the two **FastMCP servers** (cop + thief) move from a
> purely local setup to **public HTTPS** endpoints, so that the orchestrator can drive a full
> autonomous game over the **public internet** with **revocable token auth**. It maps directly to
> acceptance criterion **E6 — Local → cloud** and supports **E2** (two FastMCP servers + token
> auth), **E3** (Server/Client separation), **E5** (fully autonomous pipeline) and **E8**
> (config-driven, no hardcoding).
>
> **Architecture invariant (graded — E3).** Only the **MCP Servers** are deployed. The
> **orchestrator / MCP Client** — the only component that holds the **LLM (Gemini)** — always runs
> from the developer's machine and makes **outbound-only** calls to the public MCP URLs. The LLM
> never lives inside `mcp_servers/`, in any stage, local or cloud.
>
> **Platform stance (spec-accurate).** The spec (§6/§7) is **platform-agnostic**: it says deploy to
> *"Prefect Cloud **or a similar platform**"* and explicitly endorses **tunneling** (ngrok with a
> traffic policy / Basic Auth, Localtonet, or a self-hosted Nginx reverse proxy). We therefore do
> **not** over-assert a single platform. Our **simple default** is a **Cloudflare Tunnel**
> (`cloudflared` is installed); our **hosted alternative** is **Prefect Horizon / FastMCP Cloud**
> (stable URLs, better for the bonus). Both paths are first-class and selected through config.

---

## 1. Goals & non-goals

### 1.1 Goals
- **G1.** Prove the entire pipeline on **localhost** first: both MCP servers on **separate ports**,
  the orchestrator talking to them locally, a full game completing autonomously.
- **G2.** Expose both MCP servers over **public HTTPS** so the run is reachable from anywhere,
  independent of any home/campus firewall or NAT.
- **G3.** Keep the deployment **platform-agnostic**: a tunnel default plus a hosted alternative,
  both wired through `config/config.yaml` — **no URL is ever hardcoded** (Rule 4 / E8).
- **G4.** Enforce **revocable token auth** on every public endpoint and document the revocation drill.
- **G5.** Capture **CLI logs** of a live cloud run as graded evidence (feeds E10/E11).

### 1.2 Non-goals
- Not deploying the orchestrator/LLM to the cloud (it stays local; **E3**).
- Not committing to one specific vendor (the spec is agnostic — we document choices, not mandates).
- Not productionizing (no autoscaling/HA); a free-tier-friendly, reproducible setup is enough.

---

## 2. The two deployment stages

```
STAGE 1 — LOCAL                              STAGE 2 — PUBLIC HTTPS
┌───────────────────────────┐                ┌───────────────────────────┐
│ orchestrator (Gemini LLM) │  outbound      │ orchestrator (Gemini LLM) │  outbound
│   = MCP Client            │ ─────────────▶ │   = MCP Client (LOCAL)    │ ───────────────▶ INTERNET
└───────────────────────────┘                └───────────────────────────┘
        │ http://localhost                            │ https://… (tunnel or Horizon)
        ▼                                             ▼
┌──────────────┐  ┌──────────────┐           ┌──────────────┐  ┌──────────────┐
│ cop_server   │  │ thief_server │           │ cop_server   │  │ thief_server │
│ :8001/mcp    │  │ :8002/mcp    │           │ public HTTPS │  │ public HTTPS │
│ token auth   │  │ token auth   │           │ token auth   │  │ token auth   │
└──────────────┘  └──────────────┘           └──────────────┘  └──────────────┘
```

The contract is **identical across stages** — same FastMCP servers, same tools, same
`StaticTokenVerifier` token auth, same orchestrator code. Only the **transport address** changes,
and that address comes **only from config**. This is what makes "promote local → cloud" a one-line
config edit plus a `--cloud` flag, not a rewrite.

---

## 3. Stage 1 — Full local integration (localhost, separate ports)

### 3.1 What runs where
| Component | Command | Address |
|---|---|---|
| Cop MCP server | `python -m cosmos77_ex06.mcp_servers.cop_server` | `http://localhost:8001/mcp` |
| Thief MCP server | `python -m cosmos77_ex06.mcp_servers.thief_server` | `http://localhost:8002/mcp` |
| Orchestrator (LLM) | `cosmos77-pursuit run --local --games 6` | local process, outbound to the two URLs |

Ports `cop_port: 8001` / `thief_port: 8002` and the URLs `mcp.cop_url` / `mcp.thief_url` come from
`config/config.yaml`. The two servers run on **separate ports** so they are genuinely two
independent FastMCP processes (E2), exactly as they will be two independent public services in
Stage 2.

### 3.2 Token auth, local
Each server attaches `StaticTokenVerifier` (FastMCP) reading tokens from the environment:
`COP_MCP_TOKEN`, `THIEF_MCP_TOKEN`, and the caller token `ORCHESTRATOR_TOKEN`, with
`required_scopes=["read"]`. The orchestrator presents its token on every client connection. Even on
localhost we keep auth **on**, so Stage 1 exercises the exact authentication path Stage 2 depends on
— there is no "auth only in production" surprise. Secrets live in `.env` (gitignored, Rule 9);
`.env.example` ships the variable names with no values.

### 3.3 Local acceptance gate (must pass before Stage 2)
1. Both servers start on 8001/8002; `list_tools` over the FastMCP client returns the expected
   role-appropriate tool names per server.
2. A **bad/empty token is rejected** (proves auth is live), a valid `ORCHESTRATOR_TOKEN` is accepted.
3. A full **autonomous game** (`--local --games 6`) completes init → 6 valid sub-games → report
   build, with **zero manual intervention** (E5), the agents exchanging **free natural-language**
   messages each turn (E4).
4. The sanity ladder (2×2 → 3×3 → 4×4 → 5×5, via config overrides) all complete locally.

Only once Stage 1 is green do we expose anything publicly — exposing a broken pipeline just makes
debugging harder over the network.

---

## 4. Stage 2 — Public HTTPS exposure

### 4.1 Why public exposure is mandatory (the firewall / reachability requirement)
MCP URLs **cannot sit behind a corporate/campus/home firewall or NAT**. The grader (and, for the
bonus, a partner group) must be able to reach the two MCP servers from the open internet. A laptop
on a home router has a private IP and no inbound port; therefore we need one of:

- **(a) A tunnel** — an **outbound** connection from the laptop to an edge that publishes a public
  HTTPS URL and forwards traffic back down the tunnel. No inbound firewall rule needed because the
  laptop dials out. This is the spec's explicitly-endorsed approach.
- **(b) A hosted runtime** — the servers run on a provider that already has a public HTTPS endpoint.

Crucially, the **orchestrator only makes outbound calls** in both cases (it is the MCP **Client**),
so the LLM side never needs any inbound reachability — only the two MCP **Servers** are published.

### 4.2 Option A (our simple default) — Cloudflare Tunnel
`cloudflared` is installed (2026.3.0). It is the lowest-friction, spec-endorsed way to get two
public HTTPS URLs for locally-running servers.

**Procedure**
1. Start both MCP servers locally (as in Stage 1) on 8001 and 8002.
2. Open a tunnel per server:
   - `cloudflared tunnel --url http://localhost:8001` → prints a public `https://<random>.trycloudflare.com` URL → append `/mcp`.
   - `cloudflared tunnel --url http://localhost:8002` → second public URL → append `/mcp`.
3. Put those two URLs into `config/config.yaml` under `mcp.cop_url` / `mcp.thief_url`.
4. Run the orchestrator with the cloud target: `cosmos77-pursuit run --cloud --games 6`.

**Trade-off — ephemeral URLs.** Quick (unauthenticated, `--url`) Cloudflare tunnels mint a **new
random hostname on every restart**. Therefore: **the URLs are not stable, and `config.yaml` must be
updated each time the tunnel restarts.** This is acceptable for development and for capturing the
graded cloud-run logs, but it is **not ideal for the bonus**, where a stable, pre-shared URL makes
coordinating with a partner group far easier. (A named Cloudflare tunnel with a custom domain gives
stable URLs but requires a domain + account setup — out of scope for the simple default.)

**Token auth still applies.** The tunnel only transports bytes; the FastMCP `StaticTokenVerifier`
still gates every request, so an exposed `trycloudflare.com` URL without a valid token is useless to
an attacker.

### 4.3 Option B (hosted alternative) — Prefect Horizon / FastMCP Cloud
The hosted path runs the MCP servers on a managed platform with **stable** `https://*.fastmcp.app/mcp`
URLs.

**Procedure (high level)**
1. Sign in to the hosted FastMCP runtime (Horizon, GitHub sign-in) and connect this repo.
2. Create **two** services, one per server, with ASGI entrypoints exported from
   `mcp_servers/app.py` (`cop_server:mcp` and `thief_server:mcp` via `mcp.http_app()`).
3. Set `COP_MCP_TOKEN` / `THIEF_MCP_TOKEN` / `ORCHESTRATOR_TOKEN` as **platform secrets** (never in
   the repo).
4. Take the two issued `https://*.fastmcp.app/mcp` URLs and write them into `config.yaml`.
5. Run `cosmos77-pursuit run --cloud --games 6` from the local orchestrator.

**Why it's the better bonus option.** The URLs are **stable across restarts**, so a partner group
can be handed a fixed endpoint once and reuse it for the whole role-swap series — no chasing a new
hostname each run.

> **Naming note.** The spec writes "Prefect Cloud". Prefect *Cloud* is a workflow-orchestration
> product and is **not** an MCP host; the MCP-hosting product is **Prefect Horizon** (the hosted
> FastMCP runtime). We keep the spec's intent (a hosted public HTTPS endpoint) while using the
> correct component. Because the spec is **platform-agnostic** ("…or a similar platform"), choosing
> Horizon **or** a tunnel — or another equivalent host — is all spec-compliant.

### 4.4 Other spec-endorsed equivalents (for completeness)
The spec also names **ngrok** (with a traffic policy / Basic Auth on top), **Localtonet**, and a
**self-hosted Nginx reverse proxy** as acceptable tunneling/exposure methods. Any of these can
substitute for Option A without code changes — they all yield a public HTTPS URL that goes into
`config.yaml`. We standardize on Cloudflare Tunnel only because `cloudflared` is already installed;
the architecture imposes no lock-in.

---

## 5. Config-driven URLs (E8 — never hardcoded)

Every address the orchestrator dials is read through `src/cosmos77_ex06/shared/config.py` from
`config/config.yaml`:

```yaml
mcp:
  cop_url:   "http://localhost:8001/mcp"   # Stage 1; replaced with the public HTTPS URL in Stage 2
  thief_url: "http://localhost:8002/mcp"   # likewise
  cop_port:  8001
  thief_port: 8002
```

- **Promotion is a config edit, not a code change.** Moving from local → tunnel → Horizon means
  editing `mcp.cop_url` / `mcp.thief_url` only.
- **The `--local` / `--cloud` flags** select intent; the actual URLs still come from config (the
  flag may simply assert that the configured URLs are `https://` for `--cloud`). No URL literal ever
  appears in Python — grep for `http` in `src/` returns nothing but config-read code.
- **Tunnel-restart workflow:** restart `cloudflared` → copy the two new URLs → paste into
  `config.yaml` → re-run. Documented explicitly because ephemeral tunnel URLs are the one moving
  part of Option A.

---

## 6. Security model

| Concern | Control |
|---|---|
| **Public reachability without inbound firewall holes** | Outbound tunnel (Option A) or hosted runtime (Option B); the laptop never opens an inbound port. |
| **Orchestrator is outbound-only** | The MCP Client (the LLM side) only *calls out* to the MCP URLs; it needs no public address. The LLM never runs server-side (E3). |
| **Endpoint authentication** | FastMCP `StaticTokenVerifier` with `required_scopes=["read"]` on **both** servers, in **both** stages. No valid token → request rejected. |
| **Secret handling** | Tokens + `GEMINI_API_KEY` live in `.env` (local) or platform secrets (hosted); both gitignored. `.env.example` carries names only (Rule 9). |
| **Token revocation (drill)** | Rotating `COP_MCP_TOKEN` / `THIEF_MCP_TOKEN` (env or platform secret) and restarting the affected server **immediately revokes** the old token: in-flight clients holding the stale token are rejected on the next request. The orchestrator picks up the new token from `.env`. This satisfies the "revocable token auth" half of E2/E6. |
| **Transport encryption** | Stage 2 endpoints are HTTPS end-to-end (tunnel edge or platform TLS); tokens are never sent in clear over the public internet. |

---

## 7. Cloud-run evidence (feeds E10 / E11)

A short live game run against the **public** URLs must be captured as **CLI logs** — the
orchestrator's structured per-turn output (turn #, role, the free natural-language message, the tool
call, resulting position, **and the cloud MCP URL** in use). These logs are the graded proof that
the agents really coordinated over **public cloud MCP servers** (not localhost), and are embedded in
the scientific README's Deployment and Visualizations sections. The capture command is the same
pipeline as local — `cosmos77-pursuit run --cloud --games 1` — only the configured URLs differ.

---

## 8. Test strategy (no live network in CI — Rule 6)

Deployment logic is validated **without** touching the network:
- **Config selection:** assert the orchestrator reads `mcp.cop_url` / `mcp.thief_url` from config and
  attaches `ORCHESTRATOR_TOKEN`; assert that under `--cloud` the resolved URLs are HTTPS.
- **Auth path:** with a mocked FastMCP client, assert a missing/wrong token is rejected and a valid
  token is accepted (mirrors the Stage 1 gate).
- **No hardcoded URLs:** a guard test greps `src/` for inline `http(s)://…/mcp` literals and fails
  if any exist outside config-read code (enforces E8).
- All MCP/LLM/network I/O is **mocked**; `cloudflared` and Horizon are never invoked in the suite.
  Real cloud runs are manual verifications, tagged `live` and excluded from CI via `-m 'not live'`.

---

## 9. Acceptance-criteria mapping

| Criterion | How this deployment plan satisfies it |
|---|---|
| **E6 — local → cloud** | Stage 1 (localhost, separate ports) → Stage 2 (public HTTPS via Cloudflare Tunnel default **or** Prefect Horizon), token auth throughout. |
| **E2 — two FastMCP servers + revocable token auth** | Two independent servers (8001/8002 → two public URLs), `StaticTokenVerifier`, documented token-rotation revocation drill. |
| **E3 — Server/Client separation** | Only the MCP **servers** are deployed; the **orchestrator/LLM stays local** and makes outbound-only calls in every stage. |
| **E5 — fully autonomous pipeline** | The same `run` command completes init → 6 sub-games → report against either local or cloud URLs, no manual steps. |
| **E8 — config-driven, no hardcoding** | All ports/URLs read from `config/config.yaml`; promotion across stages is a config edit; a guard test forbids URL literals in code. |

---

## 10. Operational checklist

**Stage 1 (local)**
- [ ] `.env` populated (`COP_MCP_TOKEN`, `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN`, `GEMINI_API_KEY`).
- [ ] Cop server up on 8001, thief server up on 8002; `list_tools` works; bad token rejected.
- [ ] `cosmos77-pursuit run --local --games 6` completes autonomously; sanity ladder green.

**Stage 2 (public) — Option A: Cloudflare Tunnel (default)**
- [ ] Both servers running locally; `cloudflared tunnel --url http://localhost:8001` and `…8002` up.
- [ ] Two `https://*.trycloudflare.com/mcp` URLs copied into `config.yaml` (re-do on every restart).
- [ ] `cosmos77-pursuit run --cloud --games 1` succeeds; CLI logs captured to `assets/`.

**Stage 2 (public) — Option B: Prefect Horizon / FastMCP Cloud (hosted, stable URLs)**
- [ ] Two services created from `mcp_servers/app.py` entrypoints; tokens set as platform secrets.
- [ ] Two stable `https://*.fastmcp.app/mcp` URLs in `config.yaml`.
- [ ] `cosmos77-pursuit run --cloud --games 6` succeeds; preferred path for the inter-group bonus.

**Always**
- [ ] No URL or token literal in `src/`. No secrets tracked by git.
- [ ] Token-revocation drill verified (rotate → restart → stale token rejected).
