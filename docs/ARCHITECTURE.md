# Contoso HR Agent -- Architecture Deep Dive

**Last Updated:** 2026-03-29
**Project:** `contoso-hr-agent/` within the `agents2` repository
**Course:** O'Reilly *Build Production AI Agents*
**Purpose:** Screen Microsoft Certified Trainer (MCT) candidates using a multi-agent AI pipeline


---


## 1. System Overview

The Contoso HR Agent is a FastAPI application backed by a LangGraph pipeline that orchestrates four CrewAI agents. It accepts resumes via web upload or a watched folder, evaluates them against Contoso HR policy using RAG (ChromaDB) and optional web research (Brave Search), and produces a scored disposition.

### Diagram 1 -- Full System Architecture

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
flowchart LR
    USER["User<br/>(Browser)"]
    INSPECTOR["MCP Client<br/>(Inspector)"]

    subgraph ENGINE["FastAPI Engine :8080"]
        direction TB
        WEBUI["Web UI<br/>chat.html / candidates.html / runs.html"]
        API["REST API<br/>/api/chat  /api/upload  /api/chat/sessions<br/>/api/candidates  /api/stats"]
    end

    subgraph PIPELINE_CLUSTER["LangGraph Pipeline"]
        direction TB
        N1["intake"]
        N2["policy_expert"]
        N3["resume_analyst"]
        N4["decision_maker"]
        N5["notify"]
        N1 --> N2 & N3
        N2 & N3 --> N4
        N4 --> N5
    end

    subgraph DATA["Data Stores"]
        direction TB
        CHROMADB[("ChromaDB<br/>data/chroma/")]
        SQLITE_HR[("SQLite<br/>data/hr.db")]
        SQLITE_CP[("SQLite<br/>data/checkpoints.db")]
        CHAT_JSON["JSON Files<br/>data/chat_sessions/"]
    end

    AZURE{{"Azure AI Foundry<br/>gpt-4-1-mini<br/>text-embedding-3-large"}}
    style AZURE fill:#50B0F0,color:#004E8C,stroke:#004E8C

    MCP_SERVER["FastMCP 2<br/>SSE :8081"]
    style MCP_SERVER fill:#0078D4,color:#FFFFFF,stroke:#004E8C

    WATCHER["File Watcher<br/>data/incoming/"]
    style WATCHER fill:#107C10,color:#FFFFFF,stroke:#107C10

    BRAVE{{"Brave Search API"}}
    style BRAVE fill:#C08000,color:#FFFFFF,stroke:#C08000

    USER --> WEBUI
    USER --> API
    API --> PIPELINE_CLUSTER
    WATCHER --> PIPELINE_CLUSTER
    INSPECTOR --> MCP_SERVER
    MCP_SERVER --> SQLITE_HR
    MCP_SERVER --> CHROMADB

    N2 --> CHROMADB
    N3 --> BRAVE
    N5 --> SQLITE_HR
    PIPELINE_CLUSTER --> SQLITE_CP
    API --> CHAT_JSON
    PIPELINE_CLUSTER --> AZURE
    N2 --> AZURE
    CHROMADB --> AZURE

    style ENGINE fill:#0078D4,color:#FFFFFF,stroke:#004E8C
    style PIPELINE_CLUSTER fill:#E8E8E8,color:#000000,stroke:#767676
    style DATA fill:#F3F2F1,color:#000000,stroke:#767676
```

**Key points:**

- The FastAPI engine serves the static web UI (chat.html, candidates.html, runs.html) and the REST API on port 8080. On startup it prints all 4 URIs: Web UI, API, Docs, MCP SSE.
- The file watcher is a separate process that polls `data/incoming/` and feeds resumes into the same LangGraph pipeline.
- The FastMCP 2 server on port 8081 exposes tools, resources, and prompts for MCP-compatible clients (e.g., MCP Inspector).
- All LLM and embedding calls route through Azure AI Foundry.


---


## 2. The Four Agents

The system uses four CrewAI agents, each defined as a class in `pipeline/agents.py` with `ROLE`, `GOAL`, `BACKSTORY`, and a `create()` classmethod.

| # | Agent Class | Persona | Context | Tools |
|---|-------------|---------|---------|-------|
| 1 | `ChatConciergeAgent` | "Alex" -- HR Chat Concierge | Interactive Q&A via `/api/chat` | `query_hr_policy` |
| 2 | `PolicyExpertAgent` | HR Policy Expert | Pipeline node 2 | `query_hr_policy` |
| 3 | `ResumeAnalystAgent` | Senior Talent Acquisition Specialist | Pipeline node 3 | `brave_web_search` |
| 4 | `DecisionMakerAgent` | Hiring Committee Chair | Pipeline node 4 | _(none -- pure reasoning)_ |

### Diagram 2 -- Agent Interaction

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
flowchart TD
    subgraph CHAT["Chat Path (interactive)"]
        direction LR
        CONCIERGE["ChatConciergeAgent<br/>&quot;Alex&quot;<br/>HR Chat Concierge"]
        TOOL_POLICY_CHAT["query_hr_policy<br/>(ChromaDB)"]
        CONCIERGE -->|"calls"| TOOL_POLICY_CHAT
    end
    style CHAT fill:#0078D4,color:#FFFFFF,stroke:#004E8C

    subgraph PIPE["Pipeline Path (batch evaluation)"]
        direction TB

        subgraph PE["Node 2: PolicyExpert"]
            POLICY_AGENT["PolicyExpertAgent<br/>HR Policy Expert"]
            TOOL_POLICY_PIPE["query_hr_policy<br/>(ChromaDB)"]
            POLICY_AGENT -->|"calls"| TOOL_POLICY_PIPE
        end
        style PE fill:#107C10,color:#FFFFFF,stroke:#107C10

        subgraph RA["Node 3: ResumeAnalyst"]
            ANALYST_AGENT["ResumeAnalystAgent<br/>Sr. Talent Acquisition"]
            TOOL_BRAVE["brave_web_search<br/>(Brave API)"]
            ANALYST_AGENT -->|"calls"| TOOL_BRAVE
        end
        style RA fill:#5DB85D,color:#FFFFFF,stroke:#107C10

        subgraph DM["Node 4: DecisionMaker"]
            DECISION_AGENT["DecisionMakerAgent<br/>Hiring Committee Chair<br/>(no tools)"]
        end
        style DM fill:#C08000,color:#FFFFFF,stroke:#C08000

        PE --> DM
        RA --> DM
    end

    POLICY_AGENT -->|"produces"| PC["PolicyContext<br/>chunks + sources"]
    ANALYST_AGENT -->|"produces"| CE["CandidateEval<br/>scores + strengths + red flags"]
    DECISION_AGENT -->|"produces"| HD["HRDecision<br/>disposition + reasoning + score"]

    style PC fill:#E8E8E8,color:#000000,stroke:#767676
    style CE fill:#E8E8E8,color:#000000,stroke:#767676
    style HD fill:#E8E8E8,color:#000000,stroke:#767676
```

**Agent-tool mapping:**

- `query_hr_policy` -- wraps `knowledge/retriever.py`, performs semantic search against ChromaDB using Azure `text-embedding-3-large`. Shared by ChatConcierge and PolicyExpert.
- `brave_web_search` -- calls the Brave Search API via `httpx` for candidate/company verification. Used only by ResumeAnalyst. Gracefully degrades if `BRAVE_API_KEY` is not set.


---


## 3. LangGraph Pipeline

The pipeline is a `StateGraph` with five nodes and a parallel fan-out/fan-in pattern. All state is carried in `HRState` (a `TypedDict`). After `intake`, `policy_expert` and `resume_analyst` run **concurrently** (independent fan-out). Both must complete before `decision_maker` (fan-in). Each crew node creates a single-agent `Crew`, calls `kickoff()`, parses the JSON output, and merges it back into state. Parallel nodes return ONLY their own state keys so LangGraph can safely merge the two partial updates.

### Diagram 3 -- Pipeline State Machine

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
stateDiagram-v2
    [*] --> intake : ResumeSubmission
    intake --> fork_state : validated resume dict

    state fork_state <<fork>>
    fork_state --> policy_expert
    fork_state --> resume_analyst

    state join_state <<join>>
    policy_expert --> join_state : + PolicyContext, policy_meta
    resume_analyst --> join_state : + CandidateEval

    join_state --> decision_maker
    decision_maker --> notify : + HRDecision
    notify --> [*] : EvaluationResult

    state intake {
        [*] --> validate_resume
        validate_resume --> set_run_metadata
        set_run_metadata --> [*]
    }

    state policy_expert {
        [*] --> create_crew_pe
        create_crew_pe --> kickoff_pe
        kickoff_pe --> parse_json_pe
        parse_json_pe --> [*]
    }
    note right of policy_expert : Tool: query_hr_policy

    state resume_analyst {
        [*] --> create_crew_ra
        create_crew_ra --> kickoff_ra
        kickoff_ra --> parse_json_ra
        parse_json_ra --> [*]
    }
    note right of resume_analyst : Tool: brave_web_search

    state decision_maker {
        [*] --> create_crew_dm
        create_crew_dm --> kickoff_dm
        kickoff_dm --> parse_json_dm
        parse_json_dm --> [*]
    }
    note right of decision_maker : No tools (pure reasoning)

    state notify {
        [*] --> assemble_result
        assemble_result --> log_summary
        log_summary --> [*]
    }

    state error_handling {
        [*] --> error_result
        error_result --> [*]
    }
    note left of error_handling : Any node can set state["error"]
```

**Error handling:** If any node encounters an exception, it sets `state["error"]` and returns. Subsequent crew nodes short-circuit when `state.get("error")` is truthy. The `notify` node detects the error and assembles a minimal `EvaluationResult` with `decision="Needs Review"` and the error message in `red_flags`.

**Checkpointing:** `SqliteSaver` writes a checkpoint to `data/checkpoints.db` after each node transition. The `thread_id` in the LangGraph config corresponds to the `session_id` on the `ResumeSubmission`, enabling per-session state recovery.

**JSON extraction:** CrewAI agent output is free-form text. The `_extract_json()` helper tries three strategies in order: direct `json.loads`, markdown code block extraction, outermost brace extraction.


---


## 4. Data Models

All data contracts are Pydantic v2 models in `models.py`. The pipeline transforms data through a chain of progressively richer models.

### Diagram 4 -- Entity Relationship

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
erDiagram
    ResumeSubmission {
        string candidate_id PK
        string filename
        string raw_text
        string source "upload | incoming_folder"
        string session_id
    }

    PolicyContext {
        list chunks
        list sources
        string query
    }

    CandidateEval {
        int skills_match_score "0-100"
        int experience_score "0-100"
        string culture_fit_notes
        list red_flags
        list strengths
        string recommended_role
        string web_research_notes
        string candidate_name
    }

    HRDecision {
        string decision "Strong Match | Possible Match | Needs Review | Not Qualified"
        string reasoning
        list next_steps
        string policy_compliance_notes
        int overall_score "0-100"
    }

    EvaluationResult {
        string candidate_id PK
        string run_id
        string filename
        string timestamp_utc
        string candidate_name
        float duration_seconds
    }

    candidates_table {
        string candidate_id PK
        string run_id
        string filename
        string candidate_name
        string decision
        int overall_score
        int skills_score
        int experience_score
        string source
        string completed_at
        float duration_seconds
    }

    evaluations_table {
        string candidate_id PK "FK"
        string run_id
        string result_json "full EvaluationResult JSON"
        string created_at
    }

    ResumeSubmission ||--o| PolicyContext : "retrieves"
    ResumeSubmission ||--|| CandidateEval : "evaluated into"
    CandidateEval ||--|| HRDecision : "decided by"
    EvaluationResult ||--|| CandidateEval : "contains"
    EvaluationResult ||--|| HRDecision : "contains"
    EvaluationResult ||--|| candidates_table : "persisted to"
    EvaluationResult ||--|| evaluations_table : "persisted to (full JSON)"
    candidates_table ||--|| evaluations_table : "FK candidate_id"
```

**Data flow summary:**

```
ResumeSubmission (input)
  --> PolicyContext     (ChromaDB retrieval result)
  --> CandidateEval     (skills_match_score, experience_score, strengths, red_flags)
  --> HRDecision        (disposition + reasoning + overall_score)
  --> EvaluationResult  (final composite -- written to SQLite + JSON file + served by API)
```


---


## 5. Chat Memory Architecture

The ChatConciergeAgent ("Alex") maintains conversation context through a two-layer memory system. This enables multi-turn HR policy Q&A with context continuity across page refreshes and server restarts.

### Diagram 5 -- Chat Session Flow

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
sequenceDiagram
    participant Browser
    participant FastAPI as FastAPI Engine
    participant Concierge as ChatConciergeAgent
    participant ChromaDB
    participant FS as FileSystem

    Note over Browser: User types a message

    Browser->>FastAPI: POST /api/chat {message, session_id}

    FastAPI->>FS: Load session history<br/>data/chat_sessions/{session_id}.json
    FS-->>FastAPI: [{role, content}, ...]

    FastAPI->>FastAPI: Append user message to history<br/>Build transcript (last 20 turns)

    FastAPI->>Concierge: Crew.kickoff()<br/>Task includes transcript + current message

    Concierge->>ChromaDB: query_hr_policy(question)
    ChromaDB-->>Concierge: PolicyContext (chunks + sources)

    Concierge-->>FastAPI: Agent reply text

    FastAPI->>FS: Save updated history to JSON
    FastAPI->>FastAPI: Generate contextual suggestions

    FastAPI-->>Browser: {reply, session_id, suggestions}

    Note over Browser: Store history in localStorage<br/>for instant page-reload restore
```

**Two-layer persistence:**

| Layer | Storage | Survives | Access |
|-------|---------|----------|--------|
| Client-side | `localStorage` in browser | Page reload, tab close | Instant (no round-trip) |
| Server-side | `data/chat_sessions/{session_id}.json` | Browser clear, server restart | `GET /api/chat/history/{id}`, `DELETE /api/chat/history/{id}` |

**Context window:** The last 20 turns of conversation history are formatted as a transcript and injected into the CrewAI task description, giving the concierge agent conversational continuity.


---


## 6. Deployment Architecture

The system runs locally on the developer's machine. All LLM and embedding inference is offloaded to Azure AI Foundry. There is no cloud deployment of the application itself -- it is a course demo.

### Diagram 6 -- Azure Resources

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
flowchart LR
    subgraph DEV["Developer Machine"]
        direction TB
        UV["uv project<br/>.venv"]
        FASTAPI_DEV["FastAPI :8080"]
        MCP_DEV["FastMCP :8081"]
        WATCHER_DEV["File Watcher"]
        CHROMA_LOCAL[("ChromaDB<br/>data/chroma/")]
        SQLITE_LOCAL[("SQLite<br/>data/hr.db<br/>data/checkpoints.db")]
    end
    style DEV fill:#F3F2F1,color:#000000,stroke:#767676

    subgraph AZURE_SUB["Azure Subscription"]
        direction TB
        subgraph RG["contoso-hr-rg (eastus2)"]
            direction TB
            subgraph AI_RESOURCE["contoso-hr-ai (AIServices S0)"]
                GPT["gpt-4-1-mini<br/>Chat Completion"]
                EMB["text-embedding-3-large<br/>Embeddings"]
            end
        end
    end
    style AZURE_SUB fill:#50B0F0,color:#004E8C,stroke:#004E8C
    style RG fill:#0078D4,color:#FFFFFF,stroke:#004E8C
    style AI_RESOURCE fill:#004E8C,color:#FFFFFF,stroke:#004E8C

    FASTAPI_DEV -->|"AzureChatOpenAI<br/>(langchain-openai)"| GPT
    FASTAPI_DEV -->|"AzureOpenAIEmbeddings<br/>(langchain-openai)"| EMB
    CHROMA_LOCAL -->|"embed_documents()"| EMB

    BRAVE_EXT{{"Brave Search API<br/>(optional)"}}
    style BRAVE_EXT fill:#C08000,color:#FFFFFF,stroke:#C08000
    FASTAPI_DEV -->|"httpx GET"| BRAVE_EXT
```

**Environment variables (`.env`):**

| Variable | Purpose |
|----------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint URL |
| `AZURE_AI_FOUNDRY_KEY` | API key for Azure AI Foundry |
| `AZURE_AI_FOUNDRY_CHAT_MODEL` | Chat deployment name (e.g., `gpt-4-1-mini`) |
| `AZURE_AI_FOUNDRY_EMBEDDING_MODEL` | Embedding deployment name (e.g., `text-embedding-3-large`) |
| `BRAVE_API_KEY` | Brave Search API key (optional -- degrades gracefully) |

**LLM integration pattern:** CrewAI agents use `LLM(model="azure/{deployment}", ...)` which routes through LiteLLM. LangChain nodes use `AzureChatOpenAI` directly. Embeddings use `AzureOpenAIEmbeddings`. All three share the same endpoint and API key.


---


## 7. MCP Integration

The system exposes an MCP (Model Context Protocol) server for tool-calling interoperability. A separate Brave Search integration is used internally by the ResumeAnalystAgent.

### Diagram 7 -- MCP Tool Calling

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0078D4','primaryTextColor':'#FFFFFF','primaryBorderColor':'#004E8C','lineColor':'#767676','secondaryColor':'#E8E8E8','tertiaryColor':'#F3F2F1'}}}%%
flowchart LR
    subgraph MCP_EXTERNAL["(a) FastMCP 2 Server -- external MCP clients"]
        direction TB
        INSPECTOR["MCP Inspector<br/>localhost:5173"]
        CLAUDE_DESKTOP["Claude Desktop<br/>or other MCP client"]

        subgraph MCP_SRV["FastMCP 2 SSE :8081"]
            direction TB
            T1["get_candidate()"]
            T2["list_candidates()"]
            T3["trigger_resume_evaluation()"]
            T4["query_policy()"]
            R1["schema://candidate"]
            R2["stats://evaluations"]
            R3["samples://resumes"]
            R4["config://settings"]
            P1["evaluate_resume"]
            P2["policy_query"]
        end

        INSPECTOR -->|"SSE"| MCP_SRV
        CLAUDE_DESKTOP -->|"SSE"| MCP_SRV
    end
    style MCP_EXTERNAL fill:#E8E8E8,color:#000000,stroke:#767676
    style MCP_SRV fill:#0078D4,color:#FFFFFF,stroke:#004E8C

    subgraph MCP_INTERNAL["(b) Brave Search -- internal tool"]
        direction TB
        ANALYST["ResumeAnalystAgent"]
        BRAVE_TOOL["brave_web_search<br/>(@tool in tools.py)"]
        BRAVE_API{{"Brave Search API<br/>api.search.brave.com"}}
        ANALYST -->|"CrewAI tool call"| BRAVE_TOOL
        BRAVE_TOOL -->|"httpx GET"| BRAVE_API
    end
    style MCP_INTERNAL fill:#F3F2F1,color:#000000,stroke:#767676
    style BRAVE_API fill:#C08000,color:#FFFFFF,stroke:#C08000

    MCP_SRV -->|"reads"| SQLITE[("SQLite<br/>hr.db")]
    MCP_SRV -->|"queries"| CHROMADB[("ChromaDB")]
    T3 -->|"invokes"| PIPELINE["LangGraph Pipeline"]
    style SQLITE fill:#107C10,color:#FFFFFF,stroke:#107C10
    style CHROMADB fill:#107C10,color:#FFFFFF,stroke:#107C10
```

**FastMCP 2 server capabilities:**

| Type | Name | Description |
|------|------|-------------|
| Tool | `get_candidate(candidate_id)` | Full evaluation result for one candidate |
| Tool | `list_candidates(limit, decision_filter)` | Recent evaluations, optionally filtered |
| Tool | `trigger_resume_evaluation(resume_text, filename)` | Run the full pipeline synchronously |
| Tool | `query_policy(question)` | Semantic search against ChromaDB |
| Resource | `schema://candidate` | JSON schema for `EvaluationResult` |
| Resource | `stats://evaluations` | Aggregate evaluation statistics |
| Resource | `samples://resumes` | List of sample resume files |
| Resource | `config://settings` | Current app config (no secrets) |
| Prompt | `evaluate_resume` | Structured resume evaluation prompt |
| Prompt | `policy_query` | HR policy question prompt |

**Transport:** SSE (Server-Sent Events) at `http://localhost:8081/sse`. Connect via MCP Inspector at `http://localhost:5173` or configure in Claude Desktop's MCP settings.


---


## Appendix: Key File Index

| File | Purpose |
|------|---------|
| `src/contoso_hr/engine.py` | FastAPI app, all REST endpoints, chat session memory |
| `src/contoso_hr/pipeline/graph.py` | LangGraph `StateGraph`, `HRState`, 5 node functions, `create_hr_graph()` |
| `src/contoso_hr/pipeline/agents.py` | 4 CrewAI agent classes with `create()` factory methods |
| `src/contoso_hr/pipeline/tasks.py` | CrewAI `Task` factories that inject prior state into task descriptions |
| `src/contoso_hr/pipeline/tools.py` | `@tool query_hr_policy` (ChromaDB) + `@tool brave_web_search` (Brave API) |
| `src/contoso_hr/pipeline/prompts.py` | System prompts for all 4 agents |
| `src/contoso_hr/config.py` | `Config` dataclass, Azure AI Foundry LLM/embeddings factories |
| `src/contoso_hr/models.py` | Pydantic v2 model chain: `ResumeSubmission` through `EvaluationResult` |
| `src/contoso_hr/knowledge/vectorizer.py` | Ingest policy docs into ChromaDB with Azure embeddings |
| `src/contoso_hr/knowledge/retriever.py` | `query_policy_knowledge()` -- semantic retrieval from ChromaDB |
| `src/contoso_hr/memory/sqlite_store.py` | `HRSQLiteStore` -- `candidates` + `evaluations` tables |
| `src/contoso_hr/memory/checkpoints.py` | LangGraph `SqliteSaver` checkpointer helpers |
| `src/contoso_hr/watcher/resume_watcher.py` | Polls `data/incoming/` for new resume files |
| `src/contoso_hr/watcher/process_resume.py` | Orchestrates file-to-pipeline-to-persistence flow |
| `src/contoso_hr/mcp_server/server.py` | FastMCP 2 server with tools, resources, and prompts |
| `src/contoso_hr/util/port_utils.py` | `force_kill_port()` -- called on every startup |
| `src/contoso_hr/util/token_tracking.py` | Token usage tracking utilities |
| `src/contoso_hr/logging_setup.py` | Rich-based structured logging |
