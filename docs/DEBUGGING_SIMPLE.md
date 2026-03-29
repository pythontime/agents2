# Simple Debugging Guide -- Contoso HR Agent

**Last Updated:** 2026-03-29

> **Historical note:** This file previously documented the `oreilly-agent-mvp/` project.
> All content below targets `contoso-hr-agent/`.

---

## Quick Start (3 Steps)

### Step 1: Open Debug Panel

- **Keyboard:** `Ctrl+Shift+D`
- **Mouse:** Click the bug icon in the left sidebar

### Step 2: Choose What to Debug

Click the dropdown at top of Debug panel, select:

- **HR Engine** -- FastAPI server (port 8080), serves web UI + REST API
- **HR Watcher** -- watches `data/incoming/` for resume files
- **MCP Server** -- FastMCP 2 on port 8081
- **Run Tests** -- all pytest tests

### Step 3: Start Debugging

- **Keyboard:** `F5`
- **Mouse:** Click green play button in Debug panel

When it pauses at a breakpoint, press `F10` to step through line-by-line.

---

## Debug Controls

### Start and Stop

| Action | Key | Mouse |
|--------|-----|-------|
| Start/Continue | `F5` | Green play button |
| Stop | `Shift+F5` | Red square button |
| Restart | `Ctrl+Shift+F5` | Green circle button |

### Stepping Through Code

| Action | Key | What It Does |
|--------|-----|--------------|
| Step Over | `F10` | Execute current line, stay in this file |
| Step Into | `F11` | Enter the function being called |
| Step Out | `Shift+F11` | Finish current function, go back |

### Breakpoints

| Action | Key | Mouse |
|--------|-----|-------|
| Toggle Breakpoint | `F9` | Click in gutter (left of line numbers) |

---

## Where to Set Breakpoints

### Pipeline (parallel fan-out/fan-in)

```text
contoso-hr-agent/src/contoso_hr/pipeline/graph.py

intake_node()                -- resume validation
policy_expert_crew_node()    -- ChromaDB RAG lookup (parallel)
resume_analyst_crew_node()   -- Brave web search (parallel)
decision_maker_crew_node()   -- pure reasoning (fan-in)
notify_node()                -- assemble EvaluationResult
```

### Chat

```text
contoso-hr-agent/src/contoso_hr/engine.py

POST /api/chat handler       -- session load, concierge kickoff, save
```

### MCP Server

```text
contoso-hr-agent/src/contoso_hr/mcp_server/server.py

Tool handlers: get_candidate, list_candidates, trigger_resume_evaluation, query_policy
```

---

## Inspecting Variables

When stopped at a breakpoint, you have 3 ways to see data:

### 1. Variables Pane (Easiest)

Left sidebar under Debug. Automatically shows all variables in scope.
Click arrows to expand nested objects like `state`.

### 2. Debug Console (Most Powerful)

Open with `Ctrl+Shift+Y`. Type any Python expression:

```python
state.keys()                           # What's in state?
state["resume"]                        # Resume input
state.get("policy_context")            # ChromaDB results
state.get("candidate_eval")            # Scores and red flags
state.get("hr_decision")              # Final disposition
state.get("error")                     # Pipeline error
```

### 3. Watch Expressions (Auto-Update)

Debug sidebar, Watch section. Click + to add:

```python
state.keys()
state.get("error")
```

---

## Common Scenarios

### "My breakpoint is not being hit"

- Make sure debugging is started (green play button or `F5`).
- Check the file is actually executed in the chosen config.
- Try `Ctrl+Shift+F5` to restart.

### "I stepped into a function I do not care about"

- Press `Shift+F11` (Step Out) to return to your code.

### "I want to run to a specific line"

- Right-click the line, select "Run to Cursor".
- Or set a breakpoint there and press `F5`.

---

## Ports

| Service | Port | Command |
|---------|------|---------|
| FastAPI Engine | 8080 | `uv run hr-engine` |
| FastMCP 2 SSE | 8081 | `uv run hr-mcp` |

---

## Troubleshooting

**"Module not found" errors?**
Make sure PYTHONPATH includes `contoso-hr-agent/src`. Launch configurations set this automatically.

**Unicode/encoding errors on Windows?**
Launch configs include `PYTHONIOENCODING: utf-8`.

**Breakpoint not being hit?**
Ensure debugging is started. Try setting breakpoint earlier in the file.

---

**Full Guide:** [DEBUGGING.md](DEBUGGING.md) |
**Quick Reference:** [DEBUGGING_QUICKREF.md](DEBUGGING_QUICKREF.md)
