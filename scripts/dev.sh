#!/usr/bin/env bash
# Sobe os coletores (8001, 8002), a central (8000) e o front-end em modo dev (5173).
set -euo pipefail
cd "$(dirname "$0")/.."

pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT INT TERM

cd backend
OPERATOR_BASE_URL=https://quantotempofalta.piracicabana.com.br \
  uv run uvicorn vemai.collector:create_app --factory --port 8001 & pids+=($!)
OPERATOR_BASE_URL=https://quantotempofalta.brmobilidadebs.com.br \
  uv run uvicorn vemai.collector:create_app --factory --port 8002 & pids+=($!)
COLLECTORS=piracicabana=http://localhost:8001,brmobilidadebs=http://localhost:8002 \
  uv run uvicorn vemai.central:create_app --factory --port 8000 & pids+=($!)
cd ../frontend
pnpm install --frozen-lockfile
pnpm dev --port 5173 & pids+=($!)

wait
