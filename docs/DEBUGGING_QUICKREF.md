# Debugging Quick Reference -- Contoso HR Agent

**Last Updated:** 2026-03-29

> **Historical note:** This file previously documented the `oreilly-agent-mvp/` project.
> All content below targets `contoso-hr-agent/`.

## Launch Configurations (Press F5)

| # | Config | Purpose | Key Breakpoint Locations |
|---|--------|---------|--------------------------|
| 1 | HR Engine | FastAPI server on port 8080 | `src/contoso_hr/engine.py` |
| 2 | HR Watcher | File watcher for `data/incoming/` | `src/contoso_hr/watcher/resume_watcher.py` |
| 3 | MCP Server | FastMCP 2 SSE on port 8081 | `src/contoso_hr/mcp_server/server.py` |
| 4 | Run Tests | All pytest tests | `tests/` |
| 5 | Debug Current File | Run whatever file is open | Your open file |

## Essential Breakpoints

### Pipeline (graph.py)

```python
# contoso-hr-agent/src/contoso_hr/pipeline/graph.py

# Node 1: intake
def intake_node(state):
    submission = ResumeSubmission(...)           # <-- validate input

# Node 2 + 3: PARALLEL fan-out
def policy_expert_crew_node(state):
    result = crew.kickoff()                     # <-- ChromaDB RAG
    raw_data = _extract_json(result.raw)        # <-- JSON parse

def resume_analyst_crew_node(state):
    result = crew.kickoff()                     # <-- Brave web search
    raw_data = _extract_json(result.raw)        # <-- JSON parse

# Node 4: fan-in
def decision_maker_crew_node(state):
    result = crew.kickoff()                     # <-- pure reasoning

# Node 5: notify
def notify_node(state):
    evaluation = EvaluationResult(...)          # <-- final output
```

### Chat (engine.py)

```python
# POST /api/chat handler
session_history = load_session(session_id)      # <-- history loaded
transcript = build_transcript(last_20)          # <-- context window
result = crew.kickoff()                         # <-- concierge reply
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F5** | Start debugging / Continue to next breakpoint |
| **F9** | Toggle breakpoint on current line |
| **F10** | Step Over (execute line, stay in file) |
| **F11** | Step Into (enter function call) |
| **Shift+F11** | Step Out (exit current function) |
| **Shift+F5** | Stop debugging |
| **Ctrl+Shift+Y** | Open Debug Console |

## Debug Console Commands

While stopped at a breakpoint:

```python
state.keys()                          # What's in state?
state["resume"]                       # See resume input
state.get("policy_context")           # PolicyContext from ChromaDB
state.get("candidate_eval")           # CandidateEval scores
state.get("hr_decision")             # Final disposition
state.get("error")                    # Check for pipeline errors
```

## Ports

| Service | Port | Command |
|---------|------|---------|
| FastAPI Engine | 8080 | `uv run hr-engine` |
| FastMCP 2 SSE | 8081 | `uv run hr-mcp` |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | Check PYTHONPATH includes `contoso-hr-agent/src` |
| Breakpoint not hit | Check `justMyCode: false` in launch.json |
| Encoding errors (Windows) | Launch configs include `PYTHONIOENCODING: utf-8` |

---

**Full Guide:** [DEBUGGING.md](DEBUGGING.md)
