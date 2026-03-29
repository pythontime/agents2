# Debugging Guide -- Contoso HR Agent

**Last Updated:** 2026-03-29
**Project:** `contoso-hr-agent/` within the `agents2` repository

> **Historical note:** This file previously documented the `oreilly-agent-mvp/` project
> (PM/Dev/QA issue-triage pipeline). That project is retained for reference but is no
> longer actively developed. All debugging guidance below targets `contoso-hr-agent/`.

---

## VSCode Launch Configurations

### Quick Start

1. Open `C:\github\agents2\` in VSCode (the repo root, not the subfolder).
2. Press `F5` or click the Run icon in the sidebar.
3. Select a configuration from the dropdown.
4. Set breakpoints by clicking in the gutter (left of line numbers).
5. Run and inspect variables, step through code.

### Key Debugging Targets

| # | Config | Purpose | Key Breakpoint Locations |
|---|--------|---------|--------------------------|
| 1 | HR Engine | FastAPI on port 8080 | `contoso-hr-agent/src/contoso_hr/engine.py` |
| 2 | HR Watcher | File watcher for `data/incoming/` | `contoso-hr-agent/src/contoso_hr/watcher/resume_watcher.py` |
| 3 | MCP Server | FastMCP 2 on port 8081 | `contoso-hr-agent/src/contoso_hr/mcp_server/server.py` |
| 4 | Run Tests | All pytest tests | `contoso-hr-agent/tests/` |
| 5 | Debug Current File | Whatever file is open | Your open file |

## Understanding Data Flow

### Pipeline State Flow (Parallel)

The pipeline fans out after `intake` so that `policy_expert` and `resume_analyst` run
concurrently. Both must complete before `decision_maker` (fan-in).

```
intake -> [policy_expert || resume_analyst] -> decision_maker -> notify
```

Set breakpoints at these key points in `contoso-hr-agent/src/contoso_hr/pipeline/graph.py`:

1. **`intake_node()`** -- validates `ResumeSubmission`, sets run metadata.
2. **`policy_expert_crew_node()`** -- CrewAI kickoff with `query_hr_policy` tool (ChromaDB). Produces `PolicyContext`.
3. **`resume_analyst_crew_node()`** -- CrewAI kickoff with `brave_web_search` tool. Produces `CandidateEval`.
4. **`decision_maker_crew_node()`** -- pure reasoning, renders `HRDecision`.
5. **`notify_node()`** -- assembles `EvaluationResult`, logs Rich summary, persists to SQLite.

### Chat Flow

Set breakpoints in `engine.py` around the `/api/chat` endpoint:

1. Load session history from `data/chat_sessions/{session_id}.json`.
2. Build transcript (last 20 turns).
3. `ChatConciergeAgent` CrewAI kickoff with `query_hr_policy` tool.
4. Save updated history, return reply + suggestions.

### Inspecting Variables

When stopped at a breakpoint:

1. **Debug Console** (`Ctrl+Shift+Y`)
   ```python
   state["resume"]
   state.get("policy_context")
   state.get("candidate_eval")
   state.get("hr_decision")
   ```

2. **Variables Pane** -- expand `state` to see pipeline state at any node.

3. **Watch Expressions**
   - `state.keys()` -- see which nodes have populated state
   - `state.get("error")` -- check for pipeline errors

## Ports

| Service | Port | Startup |
|---------|------|---------|
| FastAPI Engine | 8080 | `uv run hr-engine` |
| FastMCP 2 SSE | 8081 | `uv run hr-mcp` |

Both services call `force_kill_port()` on startup to claim their port.

## Investigation Scenarios

### Scenario 1: Resume evaluation produces unexpected disposition

1. Start `hr-engine` with debugger.
2. Set breakpoints at the start of each crew node in `graph.py`.
3. Upload a resume via the web UI (`http://localhost:8080`).
4. Step through each agent's `crew.kickoff()` call.
5. Inspect `result.raw` to see the raw LLM output before JSON extraction.

### Scenario 2: ChromaDB retrieval returns irrelevant chunks

1. Set breakpoint in `knowledge/retriever.py` at `query_policy_knowledge()`.
2. Inspect `question` (the query sent) and the returned `PolicyContext.chunks`.
3. Check ChromaDB seeding: `uv run hr-seed --reset` to re-ingest all knowledge docs.

### Scenario 3: Chat concierge loses context

1. Set breakpoint in `engine.py` at the `/api/chat` handler.
2. Inspect `session_history` -- how many turns are loaded.
3. Check `data/chat_sessions/{session_id}.json` on disk.
4. Verify transcript truncation (last 20 turns).

### Scenario 4: MCP Inspector not connecting

1. Ensure MCP server is running: `uv run hr-mcp` (port 8081).
2. Open `http://localhost:8081/sse` in browser -- should see SSE stream.
3. Run inspector: `npx @modelcontextprotocol/inspector http://localhost:8081/sse`.

## Key Files for Debugging

```
contoso-hr-agent/src/contoso_hr/
|-- pipeline/
|   |-- graph.py          # LangGraph StateGraph, 5 nodes, parallel fan-out
|   |-- agents.py         # 4 CrewAI agent classes
|   |-- tasks.py          # CrewAI Task factories
|   |-- tools.py          # query_hr_policy + brave_web_search
|   +-- prompts.py        # System prompts for all agents
|
|-- knowledge/
|   |-- vectorizer.py     # Ingest policy docs -> ChromaDB
|   +-- retriever.py      # Semantic retrieval from ChromaDB
|
|-- memory/
|   |-- sqlite_store.py   # candidates + evaluations tables
|   +-- checkpoints.py    # LangGraph SqliteSaver
|
|-- engine.py             # FastAPI app, REST endpoints, chat
|-- models.py             # Pydantic v2 data models
|-- config.py             # Azure AI Foundry configuration
+-- mcp_server/
    +-- server.py         # FastMCP 2 SSE server
```

## VSCode Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F5` | Start debugging / Continue |
| `F9` | Toggle breakpoint |
| `F10` | Step over (next line) |
| `F11` | Step into (enter function) |
| `Shift+F11` | Step out (exit function) |
| `Ctrl+Shift+F5` | Restart debugging |
| `Shift+F5` | Stop debugging |

## Troubleshooting

### "Module not found" errors
Ensure PYTHONPATH includes `contoso-hr-agent/src`. The launch configurations should set this automatically.

### Unicode/encoding errors on Windows
The configurations include `PYTHONIOENCODING: utf-8`. If you still see encoding errors, ensure you are using the provided launch configs.

### Breakpoint not hit
- Check `justMyCode: false` in launch.json.
- Ensure the file is actually executed in the current run configuration.
- Try `stopOnEntry: true` to start from the beginning.

---

**Further Reading:**
- [VSCode Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [LangGraph State Inspection](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)
