#!/usr/bin/env bash
# Start API (8000) and web (3000) in the background. Usage: scripts/dev-up.sh [dataset]
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DS="${1:-synthetic}"
LOG="${LOG_DIR:-/tmp}"
for p in $(ps -eo pid,args | awk '/[u]vicorn cricintel.api/ {print $1}'); do kill "$p"; done
for p in $(ps -eo pid,args | awk '/[n]ext start -p 3000|[n]ext-server/ {print $1}'); do kill "$p"; done
sleep 1
MODE=$([ "$DS" = "synthetic" ] && echo TEST_SYNTHETIC || echo REAL_DATA)
(cd "$ROOT/pipeline" && CRICINTEL_MODE="$MODE" CRICINTEL_DATASET="$DS" nohup "$ROOT/.venv/bin/uvicorn" cricintel.api:app --port 8000 > "$LOG/cricintel-api.log" 2>&1 &)
(cd "$ROOT/web" && NEXT_TELEMETRY_DISABLED=1 nohup npx next start -p 3000 > "$LOG/cricintel-web.log" 2>&1 &)
for i in $(seq 1 40); do curl -sf localhost:3000/api/meta >/dev/null && { echo "up (dataset=$DS mode=$MODE)"; exit 0; }; sleep 1; done
echo "failed to start; see $LOG/cricintel-*.log"; exit 1
