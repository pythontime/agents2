#!/usr/bin/env bash
# Contoso HR Agent — Start MCP Server + MCP Inspector (Unix)
# Force-kills port 8081 first, then starts FastMCP 2 and MCP Inspector.

set -e

echo ""
echo "=== Starting Contoso HR MCP Server ==="

# Kill port 8081 (belt-and-suspenders; also done inside hr-mcp)
echo "Checking port 8081..."
if command -v fuser &>/dev/null; then
    fuser -k 8081/tcp 2>/dev/null && echo "  Killed process on port 8081" || true
elif command -v lsof &>/dev/null; then
    lsof -ti tcp:8081 | xargs kill -9 2>/dev/null && echo "  Killed process on port 8081" || true
fi
sleep 0.5

# Start MCP server in background
uv run hr-mcp &
MCP_PID=$!
echo "[mcp-server] Started (PID: $MCP_PID)"
echo "  SSE endpoint: http://localhost:8081/sse"
sleep 2

cleanup() {
    echo ""
    echo "Stopping MCP server (PID: $MCP_PID)..."
    kill "$MCP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Launch MCP Inspector if npx available
if command -v npx &>/dev/null; then
    echo ""
    echo "Launching MCP Inspector..."
    echo "  Connect to: http://localhost:8081/sse"
    echo "  Press Ctrl+C to stop"
    echo ""
    npx @modelcontextprotocol/inspector http://localhost:8081/sse
else
    echo ""
    echo "[!] npx not found — MCP Inspector not launched."
    echo "    Install Node.js from https://nodejs.org/"
    echo "    Or connect manually to: http://localhost:8081/sse"
    echo ""
    echo "Press Ctrl+C to stop the MCP server."
    wait "$MCP_PID"
fi
