#!/usr/bin/env bash
# Best-effort: read the default environment's secret key from the Nango DB.
# Nango versions differ (plaintext vs encrypted vs hashed), so if this can't find
# a usable key, it tells you to grab it from the dashboard instead.
set -euo pipefail
cd "$(dirname "$0")"
[[ -f .env ]] && set -a && . ./.env && set +a
DB_USER="${NANGO_DB_USER:-nango}"; DB_NAME="${NANGO_DB_NAME:-nango}"

if ! docker ps --format '{{.Names}}' | grep -q '^nango-db$'; then
  echo "nango-db is not running. Start the stack first: docker compose up -d"; exit 1
fi

echo "Environments in DB:"
docker exec nango-db psql -U "$DB_USER" -d "$DB_NAME" -c \
  "select id, name from _nango_environments order by id;" 2>/dev/null || {
    echo "Could not query _nango_environments (schema not migrated yet?)."; }

echo
echo "Trying to surface a secret key column:"
docker exec nango-db psql -U "$DB_USER" -d "$DB_NAME" -At -c \
  "select column_name from information_schema.columns
   where table_name='_nango_environments' and column_name ilike '%secret%';" 2>/dev/null || true

echo
cat <<'EOF'
If a plaintext 'secret_key' is shown above you can read it with:
  docker exec nango-db psql -U nango -d nango -At -c \
    "select secret_key from _nango_environments order by id limit 1;"

Otherwise (key is encrypted/hashed in this Nango build), get it from the dashboard:
  http://localhost:3003  ->  Environment Settings  ->  Secret Key
Then put it in ../mcp-server/.env as NANGO_SECRET_KEY.
EOF
