#!/usr/bin/env bash
# live_tunnels.sh — bring the two MCP servers + public cloudflared tunnels UP,
# print the live public URLs, and point config.yaml at them.
#
# Leave this terminal OPEN for as long as you need the URLs live (a bonus
# team-test session, or a live demo for the professor). Ctrl-C tears it all down.
# When finished:  git checkout config/config.yaml   (restores the localhost defaults)
#
# NOTE: trycloudflare quick-tunnel URLs are ephemeral — they change every run and
# only live while this terminal + your laptop are on. For a 24/7 URL the professor
# can open anytime, use a hosted deploy instead (see deploy/PERSISTENT_DEPLOY.md).
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
set -a; source .env; set +a

echo "starting MCP servers…"
uv run python -m cosmos77_ex06.mcp_servers.cop_server   >/tmp/cop_srv.log   2>&1 & COP=$!
uv run python -m cosmos77_ex06.mcp_servers.thief_server >/tmp/thief_srv.log 2>&1 & THIEF=$!
cleanup() { echo; echo "tearing down…"; kill "$COP" "$THIEF" "${TCOP:-}" "${TTHIEF:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
sleep 8

echo "opening public tunnels…"
cloudflared tunnel --url http://localhost:8001 >/tmp/tcop.log   2>&1 & TCOP=$!
cloudflared tunnel --url http://localhost:8002 >/tmp/tthief.log 2>&1 & TTHIEF=$!

COPU=""; THIEFU=""
for _ in $(seq 1 45); do
  COPU=$(grep -oE 'https://[a-z0-9.-]+\.trycloudflare\.com' /tmp/tcop.log   | head -1 || true)
  THIEFU=$(grep -oE 'https://[a-z0-9.-]+\.trycloudflare\.com' /tmp/tthief.log | head -1 || true)
  [ -n "$COPU" ] && [ -n "$THIEFU" ] && break
  sleep 2
done
if [ -z "$COPU" ] || [ -z "$THIEFU" ]; then echo "tunnel failed to start — check /tmp/tcop.log /tmp/tthief.log"; exit 1; fi

python3 - "$COPU/mcp" "$THIEFU/mcp" <<'PY'
import re, sys
p = "config/config.yaml"; s = open(p).read()
s = re.sub(r"  cop_url:.*",   '  cop_url: "%s"'   % sys.argv[1], s, count=1)
s = re.sub(r"  thief_url:.*", '  thief_url: "%s"' % sys.argv[2], s, count=1)
open(p, "w").write(s)
PY

cat <<EOF

=========================================================
  LIVE  —  share these two URLs with your partner / prof
=========================================================
  COP   MCP : $COPU/mcp
  THIEF MCP : $THIEFU/mcp

  config.yaml now points at them. In another terminal:
      uv run cosmos77-pursuit run --cloud
  Shared auth token (a partner's orchestrator needs it): \$ORCHESTRATOR_TOKEN  (in .env — share it privately)
=========================================================
Leave this window OPEN. Ctrl-C tears it all down.
When finished:  git checkout config/config.yaml
EOF
wait
