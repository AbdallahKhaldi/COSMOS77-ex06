# Deploy the two MCP servers to public HTTPS — Prefect Horizon / FastMCP Cloud (E6)

> Hosted, **stable-URL** path (the preferred option for the inter-group bonus).
> Only the two **MCP servers** are deployed; the orchestrator (the LLM/Gemini side)
> always stays local and makes **outbound-only** calls to these URLs (E3). The spec
> writes "Prefect Cloud"; the MCP-hosting product is actually **Prefect Horizon** (the
> hosted FastMCP runtime) — Prefect *Cloud* is a workflow product and cannot host an
> MCP server. The spec is platform-agnostic ("Prefect Cloud **or a similar platform**"),
> so Horizon, a tunnel (`deploy/tunnel.sh`), ngrok, Localtonet, or an Nginx reverse
> proxy are all compliant; pick whichever yields two public HTTPS `…/mcp` URLs.

## 0. Prerequisites
- A GitHub account with this repo pushed (Horizon connects to GitHub).
- The two role tokens + the orchestrator token decided (kept OUT of the repo, Rule 9):
  `COP_MCP_TOKEN`, `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN`.
- The ASGI entrypoints already exist: `cosmos77_ex06.mcp_servers.cop_server:mcp` and
  `cosmos77_ex06.mcp_servers.thief_server:mcp` (and `mcp_servers/app.py` exports
  `cop_app` / `thief_app` via `mcp.http_app()` for a plain uvicorn host).

## 1. Sign in and connect the repo
1. Go to the hosted FastMCP runtime (Prefect Horizon, e.g. `horizon.prefect.io` /
   the FastMCP Cloud console) and **sign in with GitHub**.
2. **Connect / authorize** this repository (`COSMOS77-ex06`).

## 2. Create TWO services (one per server)
Create two separate services so the cop and thief run as **two independent processes**
(E2) — exactly the topology the cloud state-sync fix is built for.

| Service | Entrypoint | Notes |
|---|---|---|
| `cosmos77-cop`   | `cosmos77_ex06.mcp_servers.cop_server:mcp`   | exposes `place_barrier` (cop-only) |
| `cosmos77-thief` | `cosmos77_ex06.mcp_servers.thief_server:mcp` | no `place_barrier` (structural) |

- Python: install with `uv` (the project is `uv`-managed); the server module boots a
  FastMCP app named `mcp`. If the platform wants an ASGI app instead, point it at
  `cosmos77_ex06.mcp_servers.app:cop_app` / `:thief_app`.
- The HTTP path is `/mcp` (FastMCP's default mount).

## 3. Set the tokens as platform secrets (never in the repo)
For **each** service, add the env vars as **Horizon secrets**:
- `cosmos77-cop`:   `COP_MCP_TOKEN`, `ORCHESTRATOR_TOKEN`
- `cosmos77-thief`: `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN`

The `StaticTokenVerifier` (E2) reads these at boot. Each server requires the
`read` scope; the orchestrator token additionally carries BOTH `cop` and `thief`
scopes, which is what authorizes the orchestrator-only `sync_state` / `get_full_state`
state-mirroring tools (the cloud state-sync fix). `GEMINI_API_KEY` is **NOT** set here
— the LLM never runs server-side (E3).

## 4. Deploy and collect the two stable URLs
After both services are live, Horizon issues two **stable** HTTPS URLs of the form:

```
https://<cop-service>.fastmcp.app/mcp
https://<thief-service>.fastmcp.app/mcp
```

Stable across restarts — hand them to a partner group once for the whole bonus series.

## 5. Point the orchestrator at the cloud (config only — never hardcode, E8)
Edit `config/config.yaml` (the ONLY place URLs live):

```yaml
mcp:
  cop_url:   "https://<cop-service>.fastmcp.app/mcp"
  thief_url: "https://<thief-service>.fastmcp.app/mcp"
```

Put `ORCHESTRATOR_TOKEN` in your local `.env` (gitignored). Then run from your machine:

```bash
uv run cosmos77-pursuit run --cloud --games 1   # short capture run
uv run cosmos77-pursuit run --cloud --games 6   # full graded run
```

`--cloud` builds the FastMCP clients against the **config** URLs with
`Client(url, auth=BearerAuth(ORCHESTRATOR_TOKEN))` and refuses any non-`https://`
target. The engine owns the authoritative `GameState` and, after every turn (and at
each sub-game reset), mirrors the canonical board to BOTH services via `sync_state`,
so the two separate-process servers' `get_local_observation` stay consistent while
each still redacts the opponent (E4).

## 6. Token auth + revocation (E2/E6)
- Every request is gated by the `StaticTokenVerifier`; an exposed URL without a valid
  bearer token is useless to an attacker.
- **Revocation drill:** rotate `COP_MCP_TOKEN` / `THIEF_MCP_TOKEN` (or
  `ORCHESTRATOR_TOKEN`) in the Horizon secrets and restart the affected service —
  the old token is **immediately rejected** on the next request. Update your local
  `.env` with the new orchestrator token to keep running.

## 7. Capture the evidence (E10/E11)
`logging.show_server_url: true` (config) prints the cloud MCP URL on every turn record.
Tee the run to a file as graded proof the agents coordinated over public MCP servers:

```bash
uv run cosmos77-pursuit run --cloud --games 1 --log-file assets/cloud_run.log
```
