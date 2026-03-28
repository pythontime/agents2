# Contoso HR Agent

An O'Reilly training demo showing production AI agent patterns through a realistic HR use case: automated resume screening and HR policy Q&A.

## What it demonstrates

| Feature | Implementation |
|---------|----------------|
| **(a) Interactive chat** | Web chat UI + FastAPI `/api/chat` backed by Azure AI Foundry |
| **(b) Event-driven autonomy** | `ResumeWatcher` polls `data/incoming/` — drop a resume, pipeline runs automatically |
| **(c) Memory/state persistence** | LangGraph `SqliteSaver` checkpoints + SQLite candidate store + chat history (localStorage + server-side JSON) |
| **(d) LLM reasoning** | LangGraph StateGraph + 3 CrewAI agents (PolicyExpert, ResumeAnalyst, DecisionMaker) |
| **(e) MCP tool calling** | FastMCP 2 server (SSE) + Brave Search API tool inside ResumeAnalyst agent |

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js (for MCP Inspector, optional)
- Azure AI Foundry account with a deployed chat + embedding model

### Setup

```bash
# Windows
.\scripts\setup.ps1

# Linux/macOS
./scripts/setup.sh
```

Edit `.env` with your Azure AI Foundry credentials:
```bash
AZURE_AI_FOUNDRY_ENDPOINT=https://contoso-hr-ai.openai.azure.com/
AZURE_AI_FOUNDRY_KEY=your-api-key
AZURE_AI_FOUNDRY_CHAT_MODEL=gpt-4-1-mini
AZURE_AI_FOUNDRY_EMBEDDING_MODEL=text-embedding-3-large
```

Re-seed the knowledge base at any time:
```bash
uv run hr-seed --reset   # clears ChromaDB and re-ingests all policy docs
```

### Start

```bash
# Windows
.\scripts\start.ps1

# Linux/macOS
./scripts/start.sh
```

Open **http://localhost:8080/chat.html** in your browser.

## Demo Walkthrough

### 1. Chat with HR Assistant
Open `http://localhost:8080/chat.html` and ask policy questions:
- "What is Contoso's EEO policy?"
- "What is the salary band for a Level 3 engineer?"
- "How does the interview process work?"

### 2. Upload a Resume (Event-driven)
Click the upload area in the chat UI and upload any resume from `sample_resumes/` (e.g. `RESUME_Sarah_Chen_AZ-104_Trainer-v3.txt`). The pipeline will:
1. Validate the file
2. Run PolicyExpert (ChromaDB policy lookup)
3. Run ResumeAnalyst (Brave Search for verification)
4. Run DecisionMaker (advance/hold/reject)
5. Save results to SQLite

Or drop any `.txt` file directly into `data/incoming/` while the watcher is running.

### 3. View Candidate Results
Open `http://localhost:8080/candidates.html` — auto-refreshes every 10 seconds. Click any card for the full evaluation detail.

### 4. Memory / Persistence
Each session uses a stable `thread_id` with LangGraph `SqliteSaver`. Run the same resume twice — the second run finds prior checkpoint state.

Chat history uses two-layer persistence:
- **Client-side:** `localStorage` in the browser (instant restore on page reload)
- **Server-side:** JSON files in `data/chat_sessions/{session_id}.json` (survives browser clears)

API endpoints for chat history:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/history/{session_id}` | GET | Retrieve persisted chat history for a session |
| `/api/chat/history/{session_id}` | DELETE | Clear persisted chat history for a session |

### 5. MCP Server
```bash
.\scripts\start_mcp.ps1   # Windows
./scripts/start_mcp.sh    # Linux/macOS
```
MCP Inspector opens automatically. Try:
- `list_candidates` — see all evaluations
- `query_policy` with "What is the hiring process?"
- `trigger_resume_evaluation` with resume text from a sample file

## Project Structure

```
contoso-hr-agent/
├── src/contoso_hr/
│   ├── pipeline/           # LangGraph + CrewAI pipeline
│   │   ├── graph.py        # StateGraph: 5 nodes, SqliteSaver
│   │   ├── agents.py       # PolicyExpert, ResumeAnalyst, DecisionMaker
│   │   ├── tasks.py        # CrewAI task factories
│   │   ├── tools.py        # @tool: query_hr_policy, brave_web_search
│   │   └── prompts.py      # Agent system prompts
│   ├── knowledge/          # ChromaDB vectorization + retrieval
│   ├── watcher/            # File watcher (data/incoming/)
│   ├── memory/             # SQLite store + LangGraph checkpoints
│   ├── mcp_server/         # FastMCP 2 (SSE, port 8081)
│   ├── engine.py           # FastAPI (port 8080)
│   ├── config.py           # Azure AI Foundry config
│   └── models.py           # Pydantic v2 data contracts
├── web/                    # HTML/JS/CSS frontend
├── data/                   # Runtime data (gitignored)
├── sample_resumes/         # 13 trainer candidate resumes (RESUME_*.txt)
├── sample_knowledge/       # HR policy docs (.md, .pdf, .doc, .pptx)
└── scripts/                # Setup and launch scripts
```

## Architecture

```
Resume (file drop or upload)
    ↓
LangGraph StateGraph (graph.py)
  ┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐    ┌─────────────────┐
  │ policy_expert│    │  resume_analyst   │    │ decision_maker   │    │     notify      │
  │ CrewAI Crew  │───▶│   CrewAI Crew     │───▶│  CrewAI Crew     │───▶│  Assemble result│
  │ + ChromaDB   │    │ + Brave Search    │    │  (pure reasoning)│    │  → SQLite       │
  └──────────────┘    └───────────────────┘    └──────────────────┘    └─────────────────┘
        │                      │
   ChromaDB RAG            Brave API
   (HR policies)          (web research)
```

## Sample Resumes

The 13 `RESUME_*.txt` files in `sample_resumes/` cover three quality tiers for MCT trainer screening:

| Tier | Candidates | Description |
|------|-----------|-------------|
| **Excellent** | Sarah Chen, Alice Zhang, Rachel Torres, Tomoko Sato | Active MCT, multiple Azure/M365/Security certs, strong training metrics |
| **Mid-tier** | Bob Martinez, David Park, James Okafor, Carol Okonkwo, Priya Kapoor | Some relevant certs or experience, but gaps in training delivery or credentials |
| **Poor match** | David Kim, Kevin Walsh, Marcus Johnson, Alex Rivera | No MCT, no training experience, or entirely different career focus |

## Azure AI Foundry Deployment

| Setting | Value |
|---------|-------|
| Resource group | `contoso-hr-rg` |
| Resource name | `contoso-hr-ai` |
| Region | `eastus2` |
| Chat model | `gpt-4-1-mini` |
| Embedding model | `text-embedding-3-large` |

Teardown when finished:
```bash
az group delete --name contoso-hr-rg --yes --no-wait
```

## Remote MCP Servers (.mcp.json)

- **Azure MCP** (`@azure/mcp`) — inspect/provision Azure AI Foundry resources
- **Brave Search MCP** (`@modelcontextprotocol/server-brave-search`) — web search (also used directly in ResumeAnalystAgent)

## Extension Ideas

- Email notifications via Microsoft Graph API when a candidate is evaluated
- Add a 4th agent: InterviewScheduler that proposes calendar slots
- Connect Azure MCP to provision Foundry resources automatically in the demo
- Upgrade ChromaDB to Azure AI Search for enterprise scale
