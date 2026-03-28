# Copilot Instructions for agents2 (O'Reilly AI Agents Training)

## Project Overview
- **Purpose:** O'Reilly Live Learning course demonstrating production-ready AI agent patterns for HR resume screening, using LangGraph (stateful orchestration) and CrewAI (multi-agent collaboration), fully coupled with Azure AI Foundry.
- **Primary Project:** `contoso-hr-agent/` — Contoso HR Agent that screens Microsoft Certified Trainer resumes.
- **Legacy Reference:** `oreilly-agent-mvp/` — Earlier iteration; kept for reference only.

## Structure
- `contoso-hr-agent/` is the main Python package.
  - `src/contoso_hr_agent/` contains all core logic:
    - `pipeline/` — LangGraph + CrewAI orchestration (fully coupled)
    - `watcher/` — Folder watcher for event-driven resume processing
    - `mcp/` — FastMCP 2 server for tool exposure
    - `knowledge/` — ChromaDB vector store and document ingestion
    - `tools/` — Agent tools (ChromaDB retrieval, Brave Search)
  - `sample_resumes/` — Test resumes following `RESUME_*.txt` naming convention
  - `sample_knowledge/` — Knowledge base documents (supports `.pdf`, `.docx`, `.pptx`, `.md`)
  - `data/chat_sessions/` — Backend chat history stored as `{session_id}.json`

## Key Workflows
- **Run the HR engine (FastAPI on port 8080):**
  - `uv run hr-engine`
- **Run the folder watcher (event-driven resume processing):**
  - `uv run hr-watcher`
- **Run the MCP server (FastMCP 2 on port 8081):**
  - `uv run hr-mcp`
- **Seed the knowledge base into ChromaDB:**
  - `uv run hr-seed`
- **Environment:**
  - Copy `.env.example` to `.env` and configure Azure AI Foundry credentials
- **Dependencies:**
  - Managed via `pyproject.toml`; use `uv` for all package management

## Tech Stack
- **Orchestration:** LangGraph + CrewAI (fully coupled pipeline)
- **LLM:** Azure AI Foundry (gpt-4-1-mini)
- **Embeddings:** Azure AI Foundry (text-embedding-3-large)
- **Vector Store:** ChromaDB
- **MCP Server:** FastMCP 2
- **API Framework:** FastAPI
- **Package Manager:** uv

## CrewAI Agents
| Agent | Role | Tools |
|-------|------|-------|
| PolicyExpertAgent | Evaluates resumes against HR policies using knowledge base | ChromaDB retrieval tools |
| ResumeAnalystAgent | Researches candidate background and credentials | Brave Search tool |
| DecisionMakerAgent | Synthesizes findings into hiring recommendation | Pure reasoning (no tools) |

## Chat History
- **Frontend:** Stored in `localStorage`
- **Backend:** Persisted as JSON files in `data/chat_sessions/{session_id}.json`

## Patterns & Conventions
- **No business logic in `__init__.py`** — only imports and metadata
- **Scripts registered in `pyproject.toml`** for CLI use via `uv run`
- **Secrets:** Never commit `.env` or secrets; use environment variables
- **Resumes:** All sample resumes use `RESUME_*.txt` naming in `sample_resumes/`
- **Knowledge base:** Place `.pdf`, `.docx`, `.pptx`, or `.md` files in `sample_knowledge/`

## Integration Points
- **Azure AI Foundry:** LLM and embedding provider
- **ChromaDB:** Local vector store for policy/knowledge retrieval
- **Brave Search:** External web search for candidate research
- **FastMCP 2:** Exposes agent tools as MCP endpoints

## Examples
- To process a new resume: place a `RESUME_*.txt` file in the watched folder and run `uv run hr-watcher`
- To add a new agent: extend `pipeline/` and update CrewAI crew definition
- To add knowledge: place documents in `sample_knowledge/` and run `uv run hr-seed`

## References
- See `contoso-hr-agent/pyproject.toml` for dependencies, scripts, and build config
- See `.env.example` for environment setup
- See `contoso-hr-agent/src/contoso_hr_agent/` for all core logic

---
_Keep instructions concise and up-to-date. Update this file if workflows or architecture change._
