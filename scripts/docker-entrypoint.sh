#!/usr/bin/env bash
set -euo pipefail

cd /app
export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

python scripts/compose_preflight.py

if [[ "${SOLARPATH_SQLITE:-0}" == "1" ]]; then
  python scripts/codespaces_bootstrap.py
  exec "$@"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-solarpath}"
fi

python scripts/wait_for_db.py
python scripts/codespaces_bootstrap.py

exec "$@"
