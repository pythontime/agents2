# Contoso HR Agent -- Current State and Teaching Focus

**Last Updated:** 2026-03-29

## What Is Built

The Contoso HR Agent is a complete, working multi-agent AI pipeline for screening
Microsoft Certified Trainer (MCT) candidates. It serves as the primary teaching
demo for the O'Reilly *Build Production AI Agents* course.

### Stack

| Layer | Technology |
|-------|------------|
| Orchestration | LangGraph (StateGraph with parallel fan-out/fan-in) |
| Agent personas | CrewAI (4 agents, one Crew per LangGraph node) |
| LLM / Embeddings | Azure AI Foundry (gpt-4-1-mini + text-embedding-3-large) |
| Vector store | ChromaDB (local, seeded from policy docs) |
| Persistence | SQLite (hr.db for candidates, checkpoints.db for LangGraph) |
| Web search | Brave Search API (optional, graceful degradation) |
| MCP | FastMCP 2 (SSE on port 8081) |
| Web UI | FastAPI static files on port 8080 (chat.html, candidates.html, runs.html) |
| API | FastAPI REST -- /api/chat, /api/upload, /api/candidates, /api/stats, /api/chat/sessions, /api/health |

### Pipeline

```text
intake -> [policy_expert || resume_analyst] -> decision_maker -> notify
```

`policy_expert` and `resume_analyst` run concurrently (parallel fan-out). Both must
complete before `decision_maker` (fan-in). Four dispositions: Strong Match, Possible
Match, Needs Review, Not Qualified.

### Agents

| Agent | Role | Tools |
|-------|------|-------|
| ChatConciergeAgent ("Alex") | Interactive HR Q&A | query_hr_policy (ChromaDB) |
| PolicyExpertAgent | Pipeline -- policy assessment | query_hr_policy (ChromaDB) |
| ResumeAnalystAgent | Pipeline -- candidate scoring | brave_web_search (Brave API) |
| DecisionMakerAgent | Pipeline -- final disposition | None (pure reasoning) |

### Web Pages

- **chat.html** -- multi-turn chat with the HR Concierge ("Alex")
- **candidates.html** -- table of evaluated candidates with scores and dispositions
- **runs.html** -- Pipeline Runs trace viewer showing per-node execution details

## Teaching Focus Areas

### 1. Multi-Agent Orchestration

How LangGraph and CrewAI work together: LangGraph owns routing, state, persistence,
and parallelism. CrewAI owns persona execution (one agent + one task per node).

### 2. RAG Pipeline

ChromaDB vector store seeded from HR policy documents. The `query_hr_policy` tool
performs semantic search with Azure embeddings and returns ranked chunks.

### 3. Parallel Execution

Demonstrating fan-out/fan-in in LangGraph: independent nodes run concurrently,
each returning only its own state keys so the framework can merge safely.

### 4. MCP Integration

FastMCP 2 server exposing tools, resources, and prompts over SSE. Testable with
MCP Inspector. Shows how to make agent capabilities accessible to external clients.

### 5. Persistence and Memory

Two-layer chat memory (localStorage + server-side JSON). SQLite for candidate
evaluations. LangGraph SqliteSaver for pipeline checkpoints.

### 6. Production Patterns

Error handling with graceful degradation, port management, structured logging with
Rich, Pydantic v2 data validation, and environment-based configuration.

## Repository Layout

| Directory | Status | Purpose |
|-----------|--------|---------|
| `contoso-hr-agent/` | **Active** | Primary teaching project |
| `oreilly-agent-mvp/` | Legacy | Earlier demo (issue triage with PM/Dev/QA agents) |
| `docs/` | Active | Technical documentation (this directory) |
| `images/` | Static | Course materials |
