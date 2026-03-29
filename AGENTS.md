# Repository Guidelines

## Project Structure & Module Organization

- **`contoso-hr-agent/`** is the **only active project** -- an HR resume screening pipeline + policy Q&A system.
- `oreilly-agent-mvp/` is a **legacy** reference project (issue triage pipeline) -- retained for reference only, do not modify unless explicitly requested.
- `docs/` and `images/` hold course materials and supporting assets.
- `.github/` contains automation and repository settings.

### contoso-hr-agent/ Key Paths

- `src/contoso_hr/` holds core code (pipeline, knowledge, memory, watcher, MCP server, engine).
- `src/contoso_hr/pipeline/graph.py` implements a **parallel fan-out/fan-in** LangGraph StateGraph: `intake` fans out to `policy_expert` and `resume_analyst` (run concurrently), which fan in to `decision_maker`, then `notify`.
- `src/contoso_hr/pipeline/agents.py` defines four CrewAI agents: ChatConciergeAgent ("Alex"), PolicyExpertAgent, ResumeAnalystAgent, DecisionMakerAgent.
- `src/contoso_hr/engine.py` is the FastAPI server (port 8080) serving all API endpoints and three web pages.
- `data/` contains runtime directories: `incoming/`, `outgoing/`, `processed/`, `chroma/`, `chat_sessions/`, `checkpoints.db`, `hr.db` (all gitignored).
- `sample_resumes/` provides 13 trainer candidate resume files for local runs.
- `sample_knowledge/` provides 8 HR policy documents for ChromaDB seeding (146 chunks).
- `web/` contains three HTML/JS/CSS pages:
  - `chat.html` -- Chat with "Alex" + resume upload + "New chat" / "Clear history" buttons + Past Sessions sidebar
  - `candidates.html` -- Evaluation grid + detail modal
  - `runs.html` -- Pipeline Trace viewer (split-panel showing full execution per run including parallel branches)
- `scripts/` contains setup and launch scripts (PowerShell + bash).
- `tests/` contains pytest tests.

### Stack

LangGraph + CrewAI + FastMCP 2 + Azure AI Foundry (gpt-4-1-mini + text-embedding-3-large) + ChromaDB (146 chunks, 8 docs) + SQLite + Brave Search API

### API Endpoints

| Method | Route | Purpose |
| ------ | ----- | ------- |
| POST | `/api/chat` | Chat with ChatConcierge agent |
| POST | `/api/upload` | Upload resume to `data/incoming/` |
| GET | `/api/candidates` | List all evaluated candidates |
| GET | `/api/candidates/{id}` | Full evaluation for one candidate |
| GET | `/api/stats` | Aggregate evaluation statistics |
| GET | `/api/health` | Health check |
| GET | `/api/chat/history/{id}` | Chat history for a session |
| DELETE | `/api/chat/history/{id}` | Delete chat history for a session |
| GET | `/api/chat/sessions` | List all chat sessions |

### Ports

- Engine: 8080 (force-killed on startup)
- MCP SSE: 8081 (force-killed on startup)

### Four Dispositions

Strong Match | Possible Match | Needs Review | Not Qualified

## Build, Test, and Development Commands

From `contoso-hr-agent/`:

- `uv venv && uv sync && uv run hr-seed` sets up the environment and seeds ChromaDB.
- `.\scripts\setup.ps1` or `./scripts/setup.sh` runs full setup.
- `uv run hr-engine` starts the FastAPI server on port 8080.
- `uv run hr-watcher` starts the file watcher for `data/incoming/`.
- `uv run hr-mcp` starts the FastMCP 2 server on port 8081.
- `uv run hr-seed` re-seeds ChromaDB from `sample_knowledge/`.
- `.\scripts\start.ps1` or `./scripts/start.sh` starts engine + watcher together.
- `uv run pytest tests/ -v` runs the test suite.
- `uv run pytest --cov=contoso_hr` runs tests with coverage.

## Coding Style & Naming Conventions

- Python 3.11+, 4-space indentation, `snake_case` for modules/functions.
- `ruff` is the lint tool (line length 100, target `py311`, E/F/I/W rules).
- Pydantic v2 for all data models.
- One `Crew.kickoff()` per LangGraph node -- no nested orchestration.
- Parallel nodes must return ONLY the state keys they write (partial updates merged by LangGraph).
- Test files follow `test_*.py` naming in `tests/`.

## Testing Guidelines

- Framework: `pytest` with optional coverage via `pytest-cov`.
- Prefer tests around schema validation, pipeline steps, and knowledge retrieval.
- Use `tmp_path` fixtures; no live API calls in unit tests.
- Sample resumes and knowledge docs are available for integration tests.

## Commit & Pull Request Guidelines

- Commit messages are short and imperative (examples: "Add ...", "Refactor ...", "Update ...").
- Merge commits follow the default "Merge branch ..." format.
- PRs should describe behavior changes, link the issue, and include test results.
- If output changes, attach a sample evaluation JSON or a CLI screenshot.

## Security & Configuration Tips

- Never commit secrets. Copy `.env.example` to `.env` and set Azure AI Foundry credentials.
- Required env vars: `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, `AZURE_AI_FOUNDRY_CHAT_MODEL`, `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`.
- Optional: `BRAVE_API_KEY` for the ResumeAnalyst web search tool.
- MCP templates live in `.mcp.json` and `contoso-hr-agent/.vscode/mcp.json`.
