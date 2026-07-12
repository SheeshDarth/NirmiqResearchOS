#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/temp/runtime"
mkdir -p "$RUNTIME_DIR"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3002}"
API_HOST="${API_HOST:-127.0.0.1}"

export PYTHONPATH="${PYTHONPATH:-$ROOT/apps/api}"
export NIRMIQ_RUNTIME_PROFILE="${NIRMIQ_RUNTIME_PROFILE:-cpu_offline}"

is_listening() {
  local port="$1"
  python - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.4)
try:
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
finally:
    sock.close()
PY
}

start_api() {
  if is_listening "$API_PORT"; then
    echo "NIRMIQ API already listening on 127.0.0.1:$API_PORT"
    return
  fi
  echo "Starting NIRMIQ API on $API_HOST:$API_PORT"
  (
    cd "$ROOT/apps/api"
    python -m uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
  ) >"$RUNTIME_DIR/api.linux.out.log" 2>"$RUNTIME_DIR/api.linux.err.log" &
  echo "$!" >"$RUNTIME_DIR/api.linux.pid"
}

start_web() {
  if is_listening "$WEB_PORT"; then
    echo "NIRMIQ web already listening on 127.0.0.1:$WEB_PORT"
    return
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required for the Next.js web app." >&2
    exit 1
  fi
  echo "Starting NIRMIQ web on 127.0.0.1:$WEB_PORT"
  (
    cd "$ROOT/apps/web"
    npm run dev
  ) >"$RUNTIME_DIR/web.linux.out.log" 2>"$RUNTIME_DIR/web.linux.err.log" &
  echo "$!" >"$RUNTIME_DIR/web.linux.pid"
}

start_api
start_web

echo "NIRMIQ local browser preview:"
echo "  http://127.0.0.1:$WEB_PORT"
echo "Logs:"
echo "  $RUNTIME_DIR/api.linux.err.log"
echo "  $RUNTIME_DIR/web.linux.err.log"
