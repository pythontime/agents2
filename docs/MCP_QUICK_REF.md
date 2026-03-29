# MCP Server Quick Reference -- Contoso HR Agent

**Last Updated:** 2026-03-29

> **Historical note:** This file previously documented the `oreilly-agent-mvp/` MCP server.
> All content below targets `contoso-hr-agent/` with FastMCP 2 over SSE.

## Start Server

```bash
cd contoso-hr-agent
uv run hr-mcp              # FastMCP 2 SSE on port 8081
```

The server force-kills port 8081 on startup and listens at `http://localhost:8081/sse`.

## Test with MCP Inspector

```bash
# Requires Node.js
npx @modelcontextprotocol/inspector http://localhost:8081/sse
```

Opens a web UI (typically `http://localhost:5173`) to browse and call tools interactively.

## Tools (4)

| Tool | Parameters | Description |
|------|------------|-------------|
| `get_candidate` | `candidate_id` | Full evaluation result for one candidate |
| `list_candidates` | `limit`, `decision_filter` | Recent evaluations, optionally filtered |
| `trigger_resume_evaluation` | `resume_text`, `filename` | Run the full pipeline synchronously |
| `query_policy` | `question` | Semantic search against ChromaDB |

## Resources (4)

| Resource URI | Description |
|--------------|-------------|
| `schema://candidate` | JSON schema for `EvaluationResult` |
| `stats://evaluations` | Aggregate evaluation statistics |
| `samples://resumes` | List of sample resume files |
| `config://settings` | Current app config (no secrets) |

## Prompts (2)

| Prompt | Description |
|--------|-------------|
| `evaluate_resume` | Structured resume evaluation prompt |
| `policy_query` | HR policy question prompt |

## Ports

| Service | Port | Command |
|---------|------|---------|
| FastAPI Engine | 8080 | `uv run hr-engine` |
| FastMCP 2 SSE | 8081 | `uv run hr-mcp` |

Engine prints all 4 URIs on startup: Web UI, API, Docs, MCP SSE.

## File Locations

```text
contoso-hr-agent/
  src/contoso_hr/mcp_server/
    __init__.py
    __main__.py
    server.py            # FastMCP 2 server implementation
  scripts/
    start_mcp.sh         # Starts MCP server + Inspector
    start_mcp.ps1        # Windows variant
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8081 in use | Server force-kills port on startup; restart with `uv run hr-mcp` |
| Inspector cannot connect | Verify `http://localhost:8081/sse` is reachable |
| Tools fail with auth errors | Check `.env` has Azure AI Foundry credentials |
| ChromaDB queries return nothing | Run `uv run hr-seed` to populate the vector store |

## Documentation

- [MCP_SETUP.md](MCP_SETUP.md) -- step-by-step setup
- [MCP_INSPECTOR_GUIDE.md](MCP_INSPECTOR_GUIDE.md) -- Inspector usage
- [MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md) -- implementation details
