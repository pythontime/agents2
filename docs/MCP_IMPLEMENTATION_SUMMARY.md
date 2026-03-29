# MCP Implementation Summary

**Last Updated:** 2026-03-29

> **Historical reference.** This file originally documented the MCP server for the
> `oreilly-agent-mvp/` project (stdio transport, 5 tools for GitHub issue triage).
> That project is retained as legacy reference only.

## Current MCP Server: Contoso HR Agent

The active MCP server lives in `contoso-hr-agent/src/contoso_hr/mcp_server/server.py`.

**Transport:** SSE (Server-Sent Events) at `http://localhost:8081/sse`
**Framework:** FastMCP 2
**Port:** 8081 (force-killed on startup)
**Start command:** `uv run hr-mcp`

### Tools (4)

| Tool | Description |
|------|-------------|
| `get_candidate(candidate_id)` | Full evaluation result for one candidate |
| `list_candidates(limit, decision_filter)` | Recent evaluations, optionally filtered |
| `trigger_resume_evaluation(resume_text, filename)` | Run the full pipeline synchronously |
| `query_policy(question)` | Semantic search against ChromaDB |

### Resources (4)

| Resource URI | Description |
|--------------|-------------|
| `schema://candidate` | JSON schema for `EvaluationResult` |
| `stats://evaluations` | Aggregate evaluation statistics |
| `samples://resumes` | List of sample resume files |
| `config://settings` | Current app config (no secrets) |

### Prompts (2)

| Prompt | Description |
|--------|-------------|
| `evaluate_resume` | Structured resume evaluation prompt |
| `policy_query` | HR policy question prompt |

### Testing with MCP Inspector

```bash
# Start the MCP server first
uv run hr-mcp

# In another terminal, launch Inspector (requires Node.js)
npx @modelcontextprotocol/inspector http://localhost:8081/sse
```

The Inspector opens a web UI where you can browse and call all tools, resources, and prompts interactively.

---

For setup details, see [MCP_SETUP.md](MCP_SETUP.md).
For quick reference, see [MCP_QUICK_REF.md](MCP_QUICK_REF.md).
