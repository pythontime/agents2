# Repository Guidelines

## Project Structure & Module Organization

- `contoso-hr-agent/` is the primary Python project for the agent pipeline (HR resume screening + policy Q&A).
- `oreilly-agent-mvp/` is a legacy reference project (issue triage pipeline) -- retained for reference only.
- `docs/` and `images/` hold course materials and supporting assets.
- `.github/` contains automation and repository settings.
- `contoso-hr-agent/` key paths:
  - `src/contoso_hr/` holds core code (pipeline, knowledge, memory, watcher, MCP server, engine).
  - `data/` contains runtime directories: `incoming/`, `outgoing/`, `checkpoints.db`, `hr.db` (gitignored).
  - `sample_resumes/` provides trainer candidate resume files for local runs.
  - `sample_knowledge/` provides HR policy documents for ChromaDB seeding.
  - `web/` contains the HTML/JS/CSS frontend (chat UI, candidates page).
  - `scripts/` contains setup and launch scripts (PowerShell + bash).
  - `tests/` contains pytest tests.

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
