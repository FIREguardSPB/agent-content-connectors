#!/usr/bin/env bash
# One-command bootstrap for Personal Content Connectors.
# Idempotent: safe to re-run. Boots Nango, installs the MCP server, wires secrets,
# runs the test suite. An agent can run this unattended; a human can too.
#
#   ./setup.sh
#
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
say(){ printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn(){ printf '\033[1;33m[!] %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31m[x] %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0. prereqs
say "Checking prerequisites"
command -v docker >/dev/null || die "Docker is required. Install Docker, then re-run."
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required (docker compose ...)."
docker info >/dev/null 2>&1 || die "Docker daemon is not running. Start Docker, then re-run."
command -v openssl >/dev/null || die "openssl is required (to generate keys)."
PYBIN="$(command -v python3 || true)"; [ -n "$PYBIN" ] || die "python3 (>=3.11) is required."
HAVE_UV=0; command -v uv >/dev/null && HAVE_UV=1
echo "docker: $(docker --version)"; echo "python: $($PYBIN --version)"; echo "uv: $([ $HAVE_UV = 1 ] && uv --version || echo 'not found (will use venv+pip)')"

# ---------------------------------------------------------------- 1. Nango
say "Nango: generating secrets (.env) if needed"
( cd "$ROOT/nango" && ./setup.sh )

say "Nango: pulling images (Docker Hub can be flaky — patient retry)"
pull(){ local img="$1" n=0; docker image inspect "$img" >/dev/null 2>&1 && { echo "have $img"; return 0; }
  until [ $n -ge 20 ]; do timeout 300 docker pull "$img" >/dev/null 2>&1 && { echo "pulled $img"; return 0; }
    n=$((n+1)); warn "pull $img failed (attempt $n/20), retrying…"; sleep 6; done
  die "could not pull $img after 20 attempts (network/Docker Hub)."; }
# Read image names straight from the compose so this never drifts.
for img in $(cd "$ROOT/nango" && docker compose config --images); do pull "$img"; done

say "Nango: starting stack"
( cd "$ROOT/nango" && docker compose up -d )

say "Nango: waiting for the API to be ready"
ok=0; for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://localhost:3003/ 2>/dev/null || echo 000)
  cui=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://localhost:3009/ 2>/dev/null || echo 000)
  [ "$code" = "200" ] && { echo "API :3003 OK, Connect UI :3009 -> $cui"; ok=1; break; }
  sleep 3
done
[ "$ok" = "1" ] || warn "Nango API not responding yet on :3003 — it may still be migrating. Check: docker compose -f nango/docker-compose.yaml logs -f nango-server"

# ---------------------------------------------------------------- 2. secret -> mcp .env
say "Wiring the Nango environment secret into mcp-server/.env"
MENV="$ROOT/mcp-server/.env"
if [ -f "$MENV" ] && grep -q '^NANGO_SECRET_KEY=..' "$MENV"; then
  echo "mcp-server/.env already has NANGO_SECRET_KEY — leaving it."
else
  SK="$(docker exec nango-db psql -U nango -d nango -At -c \
        "select secret_key from _nango_environments where name='dev' limit 1;" 2>/dev/null || true)"
  if [ -n "${SK:-}" ]; then
    [ -f "$MENV" ] || cp "$ROOT/mcp-server/.env.example" "$MENV"
    if grep -q '^NANGO_SECRET_KEY=' "$MENV"; then
      sed -i "s|^NANGO_SECRET_KEY=.*|NANGO_SECRET_KEY=$SK|" "$MENV"
    else
      printf '\nNANGO_SECRET_KEY=%s\n' "$SK" >> "$MENV"
    fi
    chmod 600 "$MENV"; echo "Saved dev-environment secret to mcp-server/.env"
  else
    warn "Could not auto-extract the secret. Get it from http://localhost:3003 -> Environment Settings and put it in mcp-server/.env as NANGO_SECRET_KEY."
  fi
fi

# ---------------------------------------------------------------- 3. MCP server
say "Installing the MCP server (broker-connectors)"
cd "$ROOT/mcp-server"
if [ $HAVE_UV = 1 ]; then
  uv venv >/dev/null 2>&1 || true
  uv pip install -e ".[dev]" >/dev/null
else
  [ -d .venv ] || "$PYBIN" -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip >/dev/null
  ./.venv/bin/pip install -q -e ".[dev]" >/dev/null
fi
say "Running the test suite"
./.venv/bin/python -m pytest -q || warn "some tests failed — see output above"

# ---------------------------------------------------------------- done
cat <<EOF

$(say "Done")
Nango dashboard : http://localhost:3003   (login: admin / see nango/.env)
Connect UI      : http://localhost:3009
MCP server      : mcp-server/.venv/bin/broker-mcp   (stdio)
Connect wizard  : mcp-server/.venv/bin/broker-wizard   (opens a browser page)

Next: read AGENTS.md. To connect a first account, run the wizard and follow
docs/USER_ACTIONS.md (only manual step: create an OAuth app on the platform).
EOF
