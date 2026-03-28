# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> The root `../CLAUDE.md` contains the full architecture and command reference. This file adds context specific to working inside `oreilly-agent-mvp/` directly.

## Commands (from this directory)

```bash
# Setup
.\scripts\setup.ps1              # Windows: venv + deps
./scripts/setup.sh               # Linux/macOS

# Run
agent-menu                       # Interactive launcher
agent-mvp                        # Process one mock issue
agent-watcher                    # Start folder watcher
agent-mcp                        # Start MCP server

# Specific mock file or GitHub issue
python -m agent_mvp.pipeline.run_once --source mock --mock-file mock_issues/issue_002.json
python -m agent_mvp.pipeline.run_once --source github --repo owner/repo --issue 123

# Test & lint
pytest
pytest --cov=agent_mvp
pytest tests/test_schema.py -v
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

### Pipeline Flow

```
Issue JSON
  → [load_issue] → [pm] → [dev] → [qa] → [finalize]
  → outgoing/{issue_id}_{timestamp}.json + SQLite
```

Pipeline is `src/agent_mvp/pipeline/graph.py` (LangGraph `StateGraph`, 5 nodes).

### Key Files

| Path | Purpose |
|------|---------|
| `src/agent_mvp/pipeline/graph.py` | LangGraph state machine |
| `src/agent_mvp/pipeline/crew.py` | CrewAI variant (PM/Dev/QA personas) |
| `src/agent_mvp/pipeline/prompts.py` | System prompts — edit to change agent behaviour |
| `src/agent_mvp/models.py` | Pydantic v2: Issue → PMOutput → DevOutput → QAOutput → PipelineResult |
| `src/agent_mvp/config.py` | Config + `get_llm()` provider factory |
| `src/agent_mvp/mcp_server/server.py` | FastMCP tools exposed over stdio |
| `src/agent_mvp/util/token_tracking.py` | Per-agent token + cost tracking |

### LLM Providers

Set `LLM_PROVIDER` in `.env`: `anthropic` (default), `openai`, or `azure`. `Config.get_llm()` returns the matching LangChain chat model.

### Data Models

`models.py` defines the typed chain: `Issue → PMOutput → DevOutput → QAOutput → PipelineResult`. All inter-agent data must flow through these Pydantic v2 models.

### Folder Watcher

Drop a valid Issue JSON into `incoming/` → watcher validates, runs pipeline, writes to `outgoing/`, archives to `processed/`.

## Code Style

- Python 3.11+, `snake_case`, 4-space indent
- Ruff: line length 100, target `py311`, rules E/F/I/W
- Type hints + Google-style docstrings on all public functions
- No business logic in `__init__.py`
- Tests use `mock_issues/` fixtures; no live API calls in unit tests
