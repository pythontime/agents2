#!/usr/bin/env bash
# Contoso HR Agent — Start (Unix)
set -e

echo ""
echo "=== Starting Contoso HR Agent ==="
echo "  Web UI: http://localhost:8080/chat.html"
echo "  API:    http://localhost:8080/api/"
echo "  Press Ctrl+C to stop"
echo ""

# Start watcher in background
uv run hr-watcher &
WATCHER_PID=$!
echo "[watcher] Started (PID: $WATCHER_PID)"

# Open browser (macOS/Linux best-effort)
(sleep 3 && (open "http://localhost:8080/chat.html" 2>/dev/null || xdg-open "http://localhost:8080/chat.html" 2>/dev/null || true)) &

# Trap Ctrl+C — kill watcher on exit
cleanup() {
    echo ""
    echo "Stopping watcher (PID: $WATCHER_PID)..."
    kill "$WATCHER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start engine (foreground)
uv run hr-engine
