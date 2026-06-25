# Persistent (prof-facing) cloud deploy

The ephemeral path (`deploy/tunnel.sh` / `deploy/live_tunnels.sh`) gives public
`*.trycloudflare.com` URLs that live only while your laptop + the tunnel run, and
rotate every restart. That's ideal for a **live bonus session** with another group.

This guide is for the other need: **stable HTTPS URLs that stay up 24/7** so the
**professor can open them anytime** (even with your laptop off) and a partner group
can rely on them. That requires a *hosted* deploy.

## Recommendation

Deploy both servers to **Prefect Horizon (the rebranded FastMCP Cloud,
`horizon.prefect.io` / `fastmcp.app`)**. It clones your existing GitHub repo
(`AbdallahKhaldi/COSMOS77-ex06`), containerises each FastMCP server, and gives you a
stable `https://<name>.fastmcp.app/mcp` URL on Prefect's infrastructure — no laptop,
no domain to buy, free personal tier.

**One-time interactive steps only *you* can do** (an agent cannot — they need *your*
login): sign into `horizon.prefect.io` with **GitHub OAuth**, authorise the repo, and
create the two projects in the dashboard. After that, every redeploy rides on a normal
`git push` to `main`.

> Source confidence: the GitHub-OAuth gate, the `*.fastmcp.app/mcp` URL shape, and
> Horizon-auth-off-by-default are confirmed from gofastmcp.com. The exact
> secret-entry widget labels are **best-effort** (not verified against canonical docs).

## Repo readiness — already handled

- **`$PORT` binding — ✅ fixed in this repo.** `cop_server.py` / `thief_server.py`
  now bind `int(os.environ.get("PORT", <config port>))`, so a hosted platform that
  injects `$PORT` works, and local runs still use `mcp.cop_port` / `mcp.thief_port`.
- **Module-scope entrypoints — ✅ ready.** Both `cop_server:mcp` and
  `thief_server:mcp` are built at import time, and the ASGI variants
  `mcp_servers.app:cop_app` / `:thief_app` also exist.
- **`host` — ✅ ready.** Defaults to `0.0.0.0` (`config.yaml`).
- **`fastmcp` version — ✅ pinned.** `pyproject.toml` constrains it to `fastmcp>=3.4,<4`
  (the 3.x line), and `uv.lock` resolves it exactly to **3.4.2** — so any builder that
  respects the lock is reproducible. Do **not** loosen it to the `<3` a generic guide
  might suggest.

## Recommended path — Horizon, two projects, two URLs

You create **two** Horizon projects from the **same repo**, one per server.

### 1. Sign in (interactive — you)
Go to `https://horizon.prefect.io`, **sign in with GitHub**, authorise it to access
your repositories, and select `AbdallahKhaldi/COSMOS77-ex06`.

### 2. Create the COP project
- **Server name:** `cosmos77-cop` (becomes the public subdomain — globally unique on `fastmcp.app`).
- **Entrypoint:** `src/cosmos77_ex06/mcp_servers/cop_server.py:mcp`
- **Authentication toggle:** leave **OFF** — the server already enforces its own
  `StaticTokenVerifier` bearer token; Horizon org-auth on top would just complicate
  partner/orchestrator access.

### 3. Create the THIEF project
Repeat as a **second** project from the same repo:
- **Server name:** `cosmos77-thief`
- **Entrypoint:** `src/cosmos77_ex06/mcp_servers/thief_server.py:mcp`
- Auth toggle **OFF**.

### 4. Set the token secrets — before the first deploy of each project
Importing either entrypoint reads the tokens from the environment at load
(`mcp_servers/auth.py` `build_verifier`). A **missing** token does **not** crash the
build: `build_verifier` falls back to a fresh unguessable `secrets.token_hex(32)` so the
import succeeds, but the server then **rejects every call at runtime** (the real bearer
no longer matches). So an absent secret yields a silently-dead server, not a `KeyError`
— set the secrets correctly the first time.

Each server needs only its **own** role token plus the shared `ORCHESTRATOR_TOKEN` (this
matches `deploy/horizon.md` §3 and `auth.py`, which maps the role token to `["read", role]`
and the orchestrator token to both role scopes). Add to each project's environment:

| Project | Keys |
|---|---|
| `cosmos77-cop`   | `COP_MCP_TOKEN`, `ORCHESTRATOR_TOKEN` |
| `cosmos77-thief` | `THIEF_MCP_TOKEN`, `ORCHESTRATOR_TOKEN` |

> Changing an env var takes effect on the **next** deploy, so set the tokens correctly
> the first time.

### 5. Deploy → grab the two URLs
Horizon clones, builds (Docker), validates with `fastmcp inspect`, and deploys (usually
< 1 min). You get two stable URLs — always with the `/mcp` path:
```
https://cosmos77-cop.fastmcp.app/mcp
https://cosmos77-thief.fastmcp.app/mcp
```

### 6. Point `config.yaml` at them
The cloud run path reads `mcp.cop_url` / `mcp.thief_url`:
```yaml
mcp:
  host: "0.0.0.0"
  cop_url: "https://cosmos77-cop.fastmcp.app/mcp"
  thief_url: "https://cosmos77-thief.fastmcp.app/mcp"
  cop_port: 8001
  thief_port: 8002
```

### 7. Run against the cloud (orchestrator stays local)
```bash
uv run cosmos77-pursuit run --cloud --log-file reports/cloud_run.log
```

### Ongoing redeploys (automatable)
Once the two projects exist, **every `git push` to `main` auto-rebuilds/redeploys** both,
and a PR spins up a preview deployment. Only steps 1–3 needed your interactive login.
Caveat: a bad commit to `main` redeploys (and can briefly down) the live endpoint.

## Verify it works
```bash
uv run cosmos77-pursuit run --cloud --log-file reports/cloud_run.log
grep -iE "fastmcp\.app/mcp auth=ok" reports/cloud_run.log
```
Every turn reading `url=https://cosmos77-*.fastmcp.app/mcp auth=ok` (no `401` /
`Unauthorized`) means the tokens are wired and the endpoints are live for
your partner group and the professor. A `401` means the Horizon secret doesn't match the
token your local orchestrator sends — most often because a secret was left unset and the
server fell back to a random token (§4), so it now rejects every call.

## Security — token revocation
With Horizon auth OFF, the URLs are world-reachable; the **only** gate is the
`StaticTokenVerifier` bearer. Treat `COP_MCP_TOKEN` / `THIEF_MCP_TOKEN` /
`ORCHESTRATOR_TOKEN` (and the cross-group `BONUS_MCP_TOKEN`) as live secrets — they live
in `.env` / the Horizon secret store only, never in git. To **revoke** access after the
bonus window, rotate the token value in the Horizon dashboard and redeploy; the old token
instantly fails verification.

## Fallback A — named `cloudflared` tunnel (stable, but laptop-bound)
A fixed `https://cop.yourdomain.com/mcp` that survives reboots — but **requires a domain
you own on a free Cloudflare account**, and your machine must stay on (worse for "open
anytime without my laptop"). `*.cfargotunnel.com` alone is not reachable; a CNAME in your
own zone is mandatory.
```bash
cloudflared tunnel login                                   # one-time browser login
cloudflared tunnel create cosmos77-cop                     # prints UUID
cloudflared tunnel route dns cosmos77-cop cop.yourdomain.com
cloudflared tunnel run cosmos77-cop                        # ingress -> http://localhost:8001
```
Start both servers locally, run a tunnel per port, put the two `https://…/mcp` hostnames
into config, then `run --cloud`. `cloudflared service install` keeps the tunnels alive
across reboots.

## Fallback B — ASGI + uvicorn under any tunnel
The repo ships ASGI apps, so you can serve with uvicorn (and pass `--port` yourself,
sidestepping `$PORT`):
```bash
uvicorn cosmos77_ex06.mcp_servers.app:cop_app   --host 0.0.0.0 --port 8001
uvicorn cosmos77_ex06.mcp_servers.app:thief_app --host 0.0.0.0 --port 8002
```
Front them with the same tunnel/host as above.
