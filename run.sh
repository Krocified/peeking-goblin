#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  printf 'Missing backend virtualenv. Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n' >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/frontend/node_modules/.bin/vite" ]]; then
  printf 'Missing frontend dependencies. Run: cd frontend && npm install\n' >&2
  exit 1
fi

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

(
  cd "$ROOT_DIR/backend"
  exec "$BACKEND_PYTHON" app.py
) &
backend_pid=$!

(
  cd "$ROOT_DIR/frontend"
  exec npm run dev -- --host 127.0.0.1
) &
frontend_pid=$!

printf 'Frontend: http://localhost:5173\nBackend:  http://localhost:8787\nPress Ctrl-C to stop both.\n'
wait -n "$backend_pid" "$frontend_pid"
