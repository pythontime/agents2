# MCP Inspector Guide -- Contoso HR Agent

**Last Updated:** 2026-03-29

> **Historical note:** This file previously documented the MCP Inspector workflow for
> `oreilly-agent-mvp/` (stdio transport, issue-triage tools). All content below targets
> `contoso-hr-agent/` with FastMCP 2 over SSE on port 8081.

---

## What is MCP Inspector?

MCP Inspector is an interactive web UI for testing and debugging MCP servers. It lets you:

- Browse available tools, resources, and prompts
- Call tools with custom arguments
- View request/response details
- Debug server behavior in real-time

## Prerequisites

- **Node.js** installed (for `npx`)
- **MCP server running** on port 8081: `uv run hr-mcp`

## Starting MCP Inspector

```bash
# Terminal 1: Start the MCP server
cd contoso-hr-agent
uv run hr-mcp

# Terminal 2: Launch Inspector pointing at the SSE endpoint
npx @modelcontextprotocol/inspector http://localhost:8081/sse
```

The Inspector opens in your browser (typically at `http://localhost:5173`).

## Using the Inspector

### Tools Tab

The Contoso HR MCP server exposes 4 tools:

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_candidate` | `candidate_id` | Full evaluation result for one candidate |
| `list_candidates` | `limit`, `decision_filter` | Recent evaluations, optionally filtered |
| `trigger_resume_evaluation` | `resume_text`, `filename` | Run the full LangGraph pipeline |
| `query_policy` | `question` | Semantic search against ChromaDB |

**Example: Testing `list_candidates`**

1. Click **Tools** tab.
2. Find **list_candidates**.
3. Optionally set `limit` (e.g., 5) and `decision_filter` (e.g., "Strong Match").
4. Click **Execute**.
5. View the JSON response with candidate evaluation summaries.

**Example: Testing `query_policy`**

1. Find **query_policy**.
2. Set `question` to "What certifications does Contoso require for trainers?"
3. Click **Execute**.
4. View the PolicyContext with relevant chunks from ChromaDB.

### Resources Tab

| Resource URI | Description |
|--------------|-------------|
| `schema://candidate` | JSON schema for `EvaluationResult` |
| `stats://evaluations` | Aggregate statistics |
| `samples://resumes` | List of sample resume files |
| `config://settings` | Current app config (no secrets) |

Click **Fetch** on any resource to see its content.

### Prompts Tab

| Prompt | Description |
|--------|-------------|
| `evaluate_resume` | Structured resume evaluation prompt |
| `policy_query` | HR policy question prompt |

Fill in parameters and click **Generate** to see the formatted prompt text.

### Logs Tab

Real-time server logs showing requests, responses, errors, and progress updates.
Useful for debugging tool failures.

## Common Workflows

### Workflow 1: Verify Server Health

1. Start inspector.
2. Tools tab: call `list_candidates` with no filters.
3. Resources tab: fetch `config://settings`.
4. If both succeed, the server is healthy.

### Workflow 2: Test a Full Evaluation

1. Tools tab: call `trigger_resume_evaluation`.
2. Provide `resume_text` (paste a sample resume) and `filename`.
3. Watch the Logs tab for pipeline progress.
4. Check the returned `EvaluationResult`.

### Workflow 3: Debug a Failing Tool

1. Call the tool through Inspector.
2. Check the Logs tab for Python tracebacks.
3. Fix code in `contoso-hr-agent/src/contoso_hr/mcp_server/server.py`.
4. Restart MCP server: `uv run hr-mcp`.
5. Re-test in Inspector (refresh the page).

## Troubleshooting

### Inspector will not start

**Error:** `node: command not found`
Install Node.js from https://nodejs.org/ and retry.

### Port already in use

The MCP server calls `force_kill_port(8081)` on startup. If port 5173 (Inspector UI)
is in use, kill the process or use a different port:

```bash
npx @modelcontextprotocol/inspector --port 6173 http://localhost:8081/sse
```

### Tools do not appear

- Check that `uv run hr-mcp` is running without errors.
- Verify `http://localhost:8081/sse` is reachable in a browser (should show SSE stream).
- Check `.env` has the required Azure AI Foundry credentials.

### Tool execution fails

1. Check Logs tab for Python traceback.
2. Verify `.env` has `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, etc.
3. Check ChromaDB is seeded: `uv run hr-seed`.

---

**Related Documentation:**

- [MCP_SETUP.md](MCP_SETUP.md) -- setup guide
- [MCP_QUICK_REF.md](MCP_QUICK_REF.md) -- quick reference
- [MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md) -- implementation details
- [Official MCP Inspector docs](https://modelcontextprotocol.io/docs/tools/inspector)
