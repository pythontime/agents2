# MCP Server Setup Guide -- Contoso HR Agent

**Last Updated:** 2026-03-29

> **Historical note:** This file previously documented MCP setup for `oreilly-agent-mvp/`
> (stdio transport, pip install). All content below targets `contoso-hr-agent/` with
> FastMCP 2 over SSE.

---

## Prerequisites

1. **Python 3.11+** with `uv` installed
2. **Node.js** installed (for MCP Inspector)
3. **Azure AI Foundry credentials** in `.env` (see `.env.example`)
4. **ChromaDB seeded:** `uv run hr-seed`

## Quick Start

```bash
cd contoso-hr-agent

# First-time setup (if not already done)
uv venv && uv sync && uv run hr-seed

# Start the MCP server
uv run hr-mcp
```

The server starts on port 8081 (force-kills any existing process on that port) and
listens for SSE connections at `http://localhost:8081/sse`.

## Verify with MCP Inspector

```bash
# In a separate terminal (requires Node.js)
npx @modelcontextprotocol/inspector http://localhost:8081/sse
```

This opens a web UI where you can browse and test all tools, resources, and prompts.

## Integration with Claude Desktop

### Step 1: Locate Claude Config

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Step 2: Add Server Configuration

```json
{
  "mcpServers": {
    "contoso-hr-agent": {
      "command": "uv",
      "args": ["run", "hr-mcp"],
      "cwd": "C:/github/agents2/contoso-hr-agent"
    }
  }
}
```

Update the `cwd` path to match your actual project location.

### Step 3: Restart Claude Desktop

Close Claude completely and reopen. Look for the plug icon indicating the server
is connected.

## Integration with VS Code

Check `.vscode/mcp.json` in the workspace. Reload VS Code with `Ctrl+Shift+P` then
"Developer: Reload Window".

## Environment Variables

The MCP server shares the same `.env` as the main engine:

| Variable | Purpose |
|----------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint URL |
| `AZURE_AI_FOUNDRY_KEY` | API key |
| `AZURE_AI_FOUNDRY_CHAT_MODEL` | Chat deployment (e.g., `gpt-4-1-mini`) |
| `AZURE_AI_FOUNDRY_EMBEDDING_MODEL` | Embedding deployment (e.g., `text-embedding-3-large`) |

## Troubleshooting

### MCP server will not start

- Check `.env` exists and has valid credentials.
- Ensure `uv sync` has been run.
- Check port 8081 is not held by another process (server auto-kills it, but check).

### Inspector cannot connect

- Verify `http://localhost:8081/sse` is reachable (open in browser, should show SSE stream).
- Ensure you passed the full SSE URL to the inspector: `http://localhost:8081/sse`.

### Tools fail with errors

- Check `.env` has all required Azure credentials.
- Ensure ChromaDB is seeded: `uv run hr-seed`.
- Check server terminal for Python tracebacks.

### Claude Desktop does not show plug icon

1. Verify config JSON is valid (no trailing commas).
2. Verify `cwd` path exists.
3. Fully quit and reopen Claude (not just close window).
4. Check Claude logs: `%APPDATA%\Claude\logs\mcp*.log` (Windows) or
   `~/Library/Logs/Claude/mcp*.log` (macOS).

---

**Related Documentation:**

- [MCP_QUICK_REF.md](MCP_QUICK_REF.md) -- quick reference
- [MCP_INSPECTOR_GUIDE.md](MCP_INSPECTOR_GUIDE.md) -- Inspector usage
- [MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md) -- implementation details
