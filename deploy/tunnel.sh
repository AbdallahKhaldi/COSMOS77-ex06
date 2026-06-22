#!/usr/bin/env bash
# deploy/tunnel.sh — Cloudflare Tunnel fallback: expose the two LOCAL MCP servers
# over public HTTPS (E6). The spec-endorsed, lowest-friction option (`cloudflared`
# is already installed). Only the MCP SERVERS are published; the orchestrator/LLM
# stays local and calls these URLs outbound-only (E3).
#
# Prereqs:
#   - `.env` populated: COP_MCP_TOKEN, THIEF_MCP_TOKEN, ORCHESTRATOR_TOKEN, GEMINI_API_KEY
#   - `cloudflared` installed (verify: `cloudflared --version`)
#
# Usage:
#   bash deploy/tunnel.sh            # start both servers + both tunnels
#   (then copy the two printed https URLs into config/config.yaml -> mcp.cop_url/thief_url)
#   uv run cosmos77-pursuit run --cloud --games 1
#
# IMPORTANT — EPHEMERAL URLS: a quick (`--url`) Cloudflare tunnel mints a NEW random
# https://<random>.trycloudflare.com hostname on EVERY restart. So the URLs are NOT
# stable: re-copy them into config.yaml each time you restart this script. (For stable
# URLs use the hosted path in deploy/horizon.md.)
#
# TOKEN AUTH + REVOCATION: the tunnel only transports bytes — the FastMCP
# StaticTokenVerifier still gates every request, so an exposed trycloudflare.com URL
# without a valid token is useless. To REVOKE access, rotate COP_MCP_TOKEN /
# THIEF_MCP_TOKEN (or ORCHESTRATOR_TOKEN) in .env and restart the affected server:
# the stale token is rejected on the next request immediately.

set -euo pipefail

COP_PORT="${COP_PORT:-8001}"
THIEF_PORT="${THIEF_PORT:-8002}"

command -v cloudflared >/dev/null 2>&1 || {
  echo "ERROR: cloudflared not found. Install it (e.g. 'brew install cloudflared')." >&2
  exit 1
}

cleanup() {
  echo "Shutting down servers + tunnels..."
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting cop server on :${COP_PORT} and thief server on :${THIEF_PORT}..."
uv run python -m cosmos77_ex06.mcp_servers.cop_server &
uv run python -m cosmos77_ex06.mcp_servers.thief_server &

# Give the servers a moment to bind their ports before tunnelling.
sleep 3

echo "Opening Cloudflare tunnels (watch for the two https://*.trycloudflare.com URLs)..."
echo "  -> append '/mcp' to each printed URL and paste into config/config.yaml"
cloudflared tunnel --url "http://localhost:${COP_PORT}" &
cloudflared tunnel --url "http://localhost:${THIEF_PORT}" &

echo
echo "Both servers + tunnels are running. Copy the two https URLs (+ /mcp) into"
echo "config/config.yaml under mcp.cop_url / mcp.thief_url, then run:"
echo "    uv run cosmos77-pursuit run --cloud --games 1"
echo "Press Ctrl-C to stop everything."
wait
