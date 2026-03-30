# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Commands

```bash
# All commands run from contoso-hr-agent/ using uv (no manual venv activation needed)

# First-time setup
uv venv && uv sync && uv run hr-seed      # creates venv, installs deps, seeds ChromaDB

# Start everything (engine + watcher + MCP Inspector)
./scripts/start.sh          # Linux/macOS
.\scripts\start.ps1         # Windows PowerShell (also launches MCP Inspector on ports 5173/6274)

# Start individual services
uv run hr-engine            # FastAPI on port 8080 (kills port first)
uv run hr-watcher           # File watcher for data/incoming/
uv run hr-mcp               # FastMCP 2 server on port 8081 (kills port first)
uv run hr-seed              # Re-seed ChromaDB from sample_knowledge/
uv run hr-seed --reset      # Clear ChromaDB and re-seed from scratch

# MCP Inspector standalone (requires Node.js; not needed if using start.ps1)
npx @modelcontextprotocol/inspector uv run hr-mcp --stdio

# Tests
uv run pytest tests/ -v
uv run pytest --cov=contoso_hr

# Lint/format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Domain Context

Contoso hires **technical trainers** for Microsoft Azure, M365, and Security certification courses.
Key evaluation signals: MCT status, Azure/M365/Security certs (AZ-104, AZ-305, AZ-400, SC-300, AI-102),
training delivery volume + learner satisfaction (4.5+/5.0), curriculum development experience.

Sample resumes in `sample_resumes/` use the `RESUME_*.txt` naming convention (13 files covering excellent/mid/poor MCT trainer matches).
Knowledge docs in `sample_knowledge/` include PDFs, .docx, .pptx, and .md files. The vectorizer explicitly excludes `Contoso-HR-Policy.doc` (old binary format, replaced by -v2.docx) and `Copilot-Studio-HR-Scenario.pptx` (product deployment guide, not HR policy). Result: 8 docs, 146 chunks in ChromaDB.

## Architecture

### Pipeline Flow (5 LangGraph nodes, parallel fan-out)

```text
Resume file (.txt, .md, .pdf, .docx -- drop or web upload)
    |
LangGraph StateGraph  (pipeline/graph.py, SqliteSaver checkpoints)
  [intake]                    -> validate ResumeSubmission
      |           |
  [policy_expert] [resume_analyst]   <- PARALLEL fan-out (run concurrently)
  ChromaDB lookup  Brave web search
      |           |
      +-----+-----+
            |
  [decision_maker]  -> CrewAI Crew: DecisionMakerAgent (pure reasoning, no tools)
  [notify]          -> assemble EvaluationResult, log Rich summary
    |
data/outgoing/{candidate_id}_{ts}.json  +  data/hr.db  +  data/checkpoints.db  +  data/chat_sessions/{session_id}.json
```

**Parallel pattern:** `policy_expert` and `resume_analyst` are independent -- one queries ChromaDB, the other does web research. LangGraph fans out from `intake` to both, then fans in at `decision_maker` which waits for both to complete before rendering the final disposition. Parallel nodes return ONLY their own state keys (not `{**state, ...}`) so LangGraph can safely merge the two partial updates. `create_resume_analyst_task` accepts `Optional[PolicyContext]` and falls back to standard policy text when running in parallel without prior policy context.

**CrewAI + LangGraph coupling:** Each `*_crew_node` creates a `Crew(agents=[one_agent], tasks=[one_task], process=Process.sequential)` and calls `crew.kickoff()`. LangGraph owns routing/state/persistence; CrewAI owns persona execution.

### Four Agents

| Agent Class | Persona | Tools | Invocation | verbose |
|-------------|---------|-------|------------|---------|
| `ChatConciergeAgent` | "Alex" -- HR Chat Concierge | `query_hr_policy` (ChromaDB) | `/api/chat` endpoint in `engine.py` | `False` |
| `PolicyExpertAgent` | HR Policy Expert | `query_hr_policy` (ChromaDB) | Pipeline node 2 (`policy_expert_crew_node`) | `True` |
| `ResumeAnalystAgent` | Sr. Talent Acquisition Specialist | `brave_web_search` (Brave API) | Pipeline node 3 (`resume_analyst_crew_node`) | `True` |
| `DecisionMakerAgent` | Hiring Committee Chair | None (pure reasoning) | Pipeline node 4 (`decision_maker_crew_node`) | `True` |

### Four Dispositions

The DecisionMaker renders exactly one of these for each candidate:

| Disposition | Score Range | Next Step |
|-------------|------------|-----------|
| **Strong Match** | 80+ | Schedule interview immediately |
| **Possible Match** | 55--79 | Schedule technical screen |
| **Needs Review** | 35--54 | Recruiter follow-up before deciding |
| **Not Qualified** | below 35 | Decline with courtesy |

These are enforced as a `Literal` type in `HRDecision.decision` in `models.py`.

### Diagrams

See `README.md` for four Mermaid diagrams:

- **Diagram A** (Agent Roster) -- flowchart showing all four agents with parallel fan-out grouping for PolicyExpert and ResumeAnalyst
- **Diagram B** (Evaluation Pipeline) -- sequenceDiagram with `par` block showing policy_expert and resume_analyst firing concurrently, then fan-in at decision_maker
- **Diagram C** (Data Model Chain) -- flowchart of Pydantic model progression showing parallel branches from ResumeSubmission to both PolicyContext and CandidateEval
- **Diagram D** (Chat Memory Architecture) -- flowchart of two-layer chat persistence with Past Sessions sidebar, cross-session context injection, and `/api/chat/sessions` endpoint

### Key Files

| Path | Purpose |
|------|---------|
| `src/contoso_hr/pipeline/graph.py` | LangGraph StateGraph with parallel fan-out edges, HRState TypedDict, all 5 node functions, `create_hr_graph()`. Parallel nodes return partial state only. |
| `src/contoso_hr/pipeline/agents.py` | ChatConciergeAgent, PolicyExpertAgent, ResumeAnalystAgent, DecisionMakerAgent (CrewAI) |
| `src/contoso_hr/pipeline/tasks.py` | CrewAI Task factories (inject prior state into task descriptions). `create_resume_analyst_task` accepts `Optional[PolicyContext]` for parallel execution. |
| `src/contoso_hr/pipeline/tools.py` | `@tool query_hr_policy` (ChromaDB) + `@tool brave_web_search` (Brave API) |
| `src/contoso_hr/pipeline/prompts.py` | System prompts for all 4 agents (persona, evaluation criteria, output format) |
| `src/contoso_hr/config.py` | Config dataclass, Azure AI Foundry LLM/embeddings factory |
| `src/contoso_hr/models.py` | Full Pydantic v2 model chain: ResumeSubmission -> PolicyContext -> CandidateEval -> HRDecision -> EvaluationResult |
| `src/contoso_hr/knowledge/vectorizer.py` | Ingest policy docs (.txt/.md/.pdf/.docx/.pptx) -> Azure embeddings -> ChromaDB |
| `src/contoso_hr/knowledge/retriever.py` | `query_policy_knowledge(question, k)` -> PolicyContext |
| `src/contoso_hr/memory/sqlite_store.py` | HRSQLiteStore: candidates + evaluations tables |
| `src/contoso_hr/memory/checkpoints.py` | `get_checkpointer()`, `make_thread_config(session_id)` |
| `src/contoso_hr/engine.py` | FastAPI: /api/chat, /api/chat/sessions, /api/upload, /api/candidates, /api/stats, /api/health, GET/DELETE /api/chat/history/{id}. Prints 4 URIs on startup (Web UI, API, Docs, MCP SSE). Builds past-session context (last 6 turns from last 2 sessions) for ChatConcierge. |
| `src/contoso_hr/watcher/resume_watcher.py` | Polls data/incoming/ for .txt/.md/.pdf/.docx files every 3s |
| `src/contoso_hr/watcher/process_resume.py` | Runs LangGraph pipeline and saves result to SQLite |
| `src/contoso_hr/mcp_server/server.py` | FastMCP 2 server: all 5 MCP primitives (resources, resource templates, tools w/ sampling + elicitation, prompts). Supports SSE and stdio transport. |
| `src/contoso_hr/util/port_utils.py` | `force_kill_port(port)` -- called on every startup |
| `web/chat.html` / `web/chat.js` | Chat UI with upload, 6 suggestion buttons, new-chat/clear-history buttons, past sessions sidebar |
| `web/candidates.html` / `web/candidates.js` | Candidate results grid with auto-refresh |
| `web/runs.html` / `web/runs.js` | Pipeline Trace viewer: split-panel, left=run list, right=visual trace with parallel branches side-by-side |

### Data Model Chain

```text
ResumeSubmission (input)
  -> PolicyContext     (ChromaDB retrieval result)
  -> CandidateEval     (skills_match_score, experience_score, strengths, red_flags)
  -> HRDecision        (decision: Strong Match|Possible Match|Needs Review|Not Qualified, reasoning, next_steps, overall_score)
  -> EvaluationResult  (final -- written to SQLite + served by API)
```

### LLM Configuration (Azure AI Foundry)

All LLM calls use `AzureChatOpenAI` (from `langchain-openai`). CrewAI uses `LLM(model="azure/{deployment}", ...)` via LiteLLM. Embeddings use `AzureOpenAIEmbeddings`. All three share the same endpoint/key from `.env`.

Required env vars: `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, `AZURE_AI_FOUNDRY_CHAT_MODEL`, `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`.

Azure deployment: resource `contoso-hr-ai` in resource group `contoso-hr-rg` (eastus2). Deployed models: `gpt-4-1-mini` (chat) and `text-embedding-3-large` (embeddings). Endpoint: `https://contoso-hr-ai.cognitiveservices.azure.com/`.

### Port Management

`force_kill_port(port)` in `util/port_utils.py` is called at the top of `engine.py:main()` and `mcp_server/__main__.py:main()`. Scripts also kill ports as belt-and-suspenders. Always uses port 8080 (engine) and 8081 (MCP).

### Chat History Persistence

Two-layer pattern for chat memory:

- **Client-side:** `localStorage` in the browser -- instant restore on page reload, no server round-trip.
- **Server-side:** JSON files in `data/chat_sessions/{session_id}.json` -- survives browser clears, accessible via API.
- **Cross-session context:** The last 6 turns from the last 2 past sessions are injected into the ChatConcierge task prompt for continuity across conversations.

Session management endpoints:

- `GET /api/chat/sessions` lists all session JSON files with message count, preview, and timestamp.
- `GET /api/chat/history/{session_id}` returns the persisted history; `DELETE` clears it.

Chat UI features: "New chat" button (resets UI in-place, new session ID, no reload), "Clear history" button (wipes current session only), Past Sessions panel in right sidebar (fetches `/api/chat/sessions`, click to switch). Six suggestion buttons on initial load. Nav bar across all 3 pages: Chat | Candidates | Pipeline Runs.

### MCP Server (FastMCP 2)

Supports both SSE (`http://localhost:8081/sse`) and stdio transport (`uv run hr-mcp --stdio`). The `__main__.py` entry point accepts a `--stdio` flag to switch transport mode.

**Resources (static):** `schema://candidate`, `stats://evaluations`, `samples://resumes`, `config://settings`.
**Resource Templates (dynamic):** `candidate://{candidate_id}`, `policy://{topic}`.
**Tools:** `get_candidate`, `list_candidates`, `trigger_resume_evaluation`, `query_policy`, `generate_eval_summary` (uses **sampling** via `ctx.sample()`), `confirm_and_evaluate` (uses **elicitation** via `ctx.elicit()`).
**Prompts:** `evaluate_resume` (multi-message), `policy_query` (multi-message), `disposition_review` (uses embedded Context resource).

All five MCP primitives are covered: Resources, Resource Templates, Tools, Prompts, and Sampling/Elicitation.

## Code Conventions

- Python 3.11+, `snake_case`, 4-space indent, 100-char line limit
- Ruff for lint/format: `uv run ruff check src/ tests/`
- Pydantic v2 for all data models (`model_dump()`, `model_dump_json()`, `model_validate_json()`)
- One `Crew.kickoff()` per LangGraph node -- no nested orchestration
- Tests use `tmp_path` fixtures; no live API calls in unit tests
- `data/` directories are runtime-only -- never commit their contents (`data/incoming/`, `data/processed/`, `data/outgoing/`, `data/chroma/`, `data/knowledge/`, `data/chat_sessions/`)
