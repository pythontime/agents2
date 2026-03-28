# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

The primary project is `contoso-hr-agent/`. All active development happens there. The root-level `docs/` and `images/` are course materials only. `oreilly-agent-mvp/` is a legacy reference project (issue triage pipeline) and should not be modified unless explicitly requested.

## Working Directory

Most commands below assume you are in `contoso-hr-agent/`. Either `cd` there or prefix paths accordingly.

## Setup

```bash
# All commands run from contoso-hr-agent/ using uv (no manual venv activation needed)

# First-time setup
uv venv && uv sync && uv run hr-seed      # creates venv, installs deps, seeds ChromaDB

# Windows (PowerShell)
.\scripts\setup.ps1

# Linux/macOS
./scripts/setup.sh
```

Copy `.env.example` to `.env` and set your Azure AI Foundry credentials:
`AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, `AZURE_AI_FOUNDRY_CHAT_MODEL`, `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`.

## Build / Run Commands

```bash
# Start everything (engine + watcher)
./scripts/start.sh          # Linux/macOS
.\scripts\start.ps1         # Windows PowerShell

# Start individual services
uv run hr-engine            # FastAPI on port 8080 (kills port first)
uv run hr-watcher           # File watcher for data/incoming/
uv run hr-mcp               # FastMCP 2 server on port 8081 (kills port first)
uv run hr-seed              # Re-seed ChromaDB from sample_knowledge/

# MCP Inspector (requires Node.js)
./scripts/start_mcp.sh      # Starts MCP server + opens Inspector
.\scripts\start_mcp.ps1     # Windows
```

## Test & Lint

```bash
uv run pytest tests/ -v             # All tests
uv run pytest --cov=contoso_hr      # With coverage report

uv run ruff check src/ tests/       # Lint
uv run ruff format src/ tests/      # Format (line length 100)
```

## Architecture

### Pipeline Flow (5 nodes)

```
Resume file (.txt, .md, .pdf, .docx — drop or web upload)
    ↓
LangGraph StateGraph  (pipeline/graph.py, SqliteSaver checkpoints)
  [intake]          → validate ResumeSubmission
  [policy_expert]   → CrewAI Crew: PolicyExpertAgent + query_hr_policy tool (ChromaDB)
  [resume_analyst]  → CrewAI Crew: ResumeAnalystAgent + brave_web_search tool
  [decision_maker]  → CrewAI Crew: DecisionMakerAgent (pure reasoning, no tools)
  [notify]          → assemble EvaluationResult, log Rich summary
    ↓
data/outgoing/{candidate_id}_{ts}.json  +  data/hr.db  +  data/checkpoints.db
```

**CrewAI + LangGraph coupling:** Each `*_crew_node` creates a `Crew(agents=[one_agent], tasks=[one_task], process=Process.sequential)` and calls `crew.kickoff()`. LangGraph owns routing/state/persistence; CrewAI owns persona execution.

### Key Files

| Path | Purpose |
|------|---------|
| `src/contoso_hr/pipeline/graph.py` | LangGraph StateGraph, HRState TypedDict, all 5 node functions, `create_hr_graph()` |
| `src/contoso_hr/pipeline/agents.py` | PolicyExpertAgent, ResumeAnalystAgent, DecisionMakerAgent (CrewAI) |
| `src/contoso_hr/pipeline/tasks.py` | CrewAI Task factories (inject prior state into task descriptions) |
| `src/contoso_hr/pipeline/tools.py` | `@tool query_hr_policy` (ChromaDB) + `@tool brave_web_search` (Brave API) |
| `src/contoso_hr/pipeline/prompts.py` | Agent system prompts |
| `src/contoso_hr/config.py` | Config dataclass, Azure AI Foundry LLM/embeddings factory |
| `src/contoso_hr/models.py` | Full Pydantic v2 model chain: ResumeSubmission → PolicyContext → CandidateEval → HRDecision → EvaluationResult |
| `src/contoso_hr/knowledge/vectorizer.py` | Ingest policy docs (.txt/.md/.pdf/.doc/.pptx) → Azure embeddings → ChromaDB |
| `src/contoso_hr/knowledge/retriever.py` | `query_policy_knowledge(question, k)` → PolicyContext |
| `src/contoso_hr/memory/sqlite_store.py` | HRSQLiteStore: candidates + evaluations tables |
| `src/contoso_hr/memory/checkpoints.py` | `get_checkpointer()`, `make_thread_config(session_id)` |
| `src/contoso_hr/engine.py` | FastAPI: /api/chat, /api/upload, /api/candidates, /api/stats, /api/chat/history/{id} |
| `src/contoso_hr/watcher/resume_watcher.py` | Polls data/incoming/ for .txt/.md files |
| `src/contoso_hr/mcp_server/server.py` | FastMCP 2 server (SSE, port 8081) |
| `src/contoso_hr/util/port_utils.py` | `force_kill_port(port)` — called on every startup |

### Data Model Chain

```
ResumeSubmission (input)
  → PolicyContext     (ChromaDB retrieval result)
  → CandidateEval     (skills_match_score, experience_score, strengths, red_flags)
  → HRDecision        (decision: advance|hold|reject, reasoning, next_steps, overall_score)
  → EvaluationResult  (final — written to SQLite + served by API)
```

### LLM Configuration (Azure AI Foundry)

All LLM calls use `AzureChatOpenAI` (from `langchain-openai`). CrewAI uses `LLM(model="azure/{deployment}", ...)` via LiteLLM. Embeddings use `AzureOpenAIEmbeddings`. All three share the same endpoint/key from `.env`.

Required env vars: `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, `AZURE_AI_FOUNDRY_CHAT_MODEL`, `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`.

### Port Management

`force_kill_port(port)` in `util/port_utils.py` is called at the top of `engine.py:main()` and `mcp_server/__main__.py:main()`. Scripts also kill ports as belt-and-suspenders. Always uses port 8080 (engine) and 8081 (MCP).

### MCP Server (FastMCP 2)

SSE transport at `http://localhost:8081/sse`. Tools: `get_candidate`, `list_candidates`, `trigger_resume_evaluation`, `query_policy`. Resources: `schema://candidate`, `stats://evaluations`, `samples://resumes`, `config://settings`. Prompts: `evaluate_resume`, `policy_query`.

## Code Conventions

- Python 3.11+, `snake_case`, 4-space indent, 100-char line limit
- Ruff for lint/format: `uv run ruff check src/ tests/`
- Pydantic v2 for all data models (`model_dump()`, `model_dump_json()`, `model_validate_json()`)
- One `Crew.kickoff()` per LangGraph node — no nested orchestration
- Tests use `tmp_path` fixtures; no live API calls in unit tests
- `data/` directories are runtime-only — never commit their contents

## CLI Scripts (pyproject.toml)

```
hr-engine     →  contoso_hr.engine:main
hr-watcher    →  contoso_hr.watcher.resume_watcher:main
hr-mcp        →  contoso_hr.mcp_server:main
hr-seed       →  contoso_hr.knowledge.vectorizer:main
```

## Legacy Reference

`oreilly-agent-mvp/` contains an earlier demo (GitHub issue triage with PM/Dev/QA agents). It is retained for reference but is not the active project. Do not modify it unless explicitly asked.
