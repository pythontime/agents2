# Hour 3 Teaching Guide: MCP and Knowledge Retrieval

**Goal:** Students configure the FastMCP 2 server, test it with the MCP Inspector, connect it to Claude Desktop, and deep-dive into the ChromaDB knowledge retrieval system using vibe coding with Claude Code.

**Time:** 60 minutes

**Active Project:** `contoso-hr-agent/` (the Contoso HR Agent for MCT resume screening)

---

## Opening (3 minutes)

**What We're Doing This Hour:**

1. Understand MCP (Model Context Protocol)
2. Configure and test our FastMCP 2 server (port 8081)
3. Connect MCP to Claude Desktop and VS Code
4. Deep-dive into how ChromaDB powers the policy_expert agent
5. **Vibe code** a new knowledge feature with Claude Code

**Key Message:** "MCP is how you give AI assistants superpowers. ChromaDB is how you give them memory. We're doing both."

---

## What is MCP? (10 minutes)

### The Problem MCP Solves

**Draw on whiteboard:**

```text
Before MCP:
+----------+     +----------+     +----------+
| Claude   |     | Copilot  |     | Cursor   |
+----+-----+     +----+-----+     +----+-----+
     |                |                |
     v                v                v
  Custom           Custom           Custom
Integration      Integration      Integration
     |                |                |
     v                v                v
+------------------------------------------+
|           Your Application               |
+------------------------------------------+

After MCP:
+----------+     +----------+     +----------+
| Claude   |     | Copilot  |     | Cursor   |
+----+-----+     +----+-----+     +----+-----+
     |                |                |
     +----------------+----------------+
                      v
               +--------------+
               |  MCP Server  | <-- One integration
               +--------------+
                      |
                      v
               +--------------+
               | Your App     |
               +--------------+
```

**Say:** "MCP is a standard protocol. Build once, connect to any AI assistant."

### MCP Architecture

**Three components:**

| Component | Role | Example |
| --- | --- | --- |
| **Server** | Exposes tools, resources, prompts | Our FastMCP 2 server on port 8081 |
| **Client** | Calls tools, reads resources | Claude Desktop, VS Code, MCP Inspector |
| **Transport** | Communication layer | SSE (our server), stdio (local) |

### Our MCP Server Capabilities

**Show the summary:**

```text
+==========================================+
|     CONTOSO HR AGENT MCP SERVER          |
|     FastMCP 2 -- SSE on port 8081        |
+==========================================+
| TOOLS:                                   |
|  - get_candidate                         |
|  - list_candidates                       |
|  - trigger_resume_evaluation             |
|  - query_policy                          |
+------------------------------------------+
| RESOURCES:                               |
|  - schema://candidate                    |
|  - stats://evaluations                   |
|  - samples://resumes                     |
|  - config://settings                     |
+------------------------------------------+
| PROMPTS:                                 |
|  - evaluate_resume                       |
|  - policy_query                          |
+==========================================+
```

---

## Configure MCP Server (12 minutes)

### Start the Server (3 minutes)

**Verify the project is set up:**

```bash
cd agents2/contoso-hr-agent

# Check everything is installed
uv sync

# Seed the knowledge base (if not done already)
uv run hr-seed
```

**Start the MCP server:**

```bash
# CLI command (registered in pyproject.toml)
uv run hr-mcp
# Starts FastMCP 2 on http://localhost:8081/sse
```

**Start the engine in a separate terminal (for full functionality):**

```bash
uv run hr-engine
# FastAPI on http://localhost:8080
```

### Test with MCP Inspector (5 minutes)

**Launch the inspector (requires Node.js):**

```bash
# Linux / macOS
./scripts/start_mcp.sh

# Windows PowerShell
.\scripts\start_mcp.ps1
```

**In the browser:**

1. Navigate to the Tools tab
2. Click "query_policy" -- enter a question like "What certifications are required?"
3. Click "Run" -- see ChromaDB results returned
4. Click "list_candidates" -- see evaluated candidates from the database

**Try other tools:**

- `get_candidate` with a candidate ID from the list
- `trigger_resume_evaluation` with resume text

**Say:** "The Inspector lets you test MCP tools interactively before connecting to Claude Desktop. This is your debugging UI for MCP."

### Connect to Claude Desktop (4 minutes)

**Find the config file:**

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Add server configuration:**

```json
{
  "mcpServers": {
    "contoso-hr-agent": {
      "command": "uv",
      "args": ["run", "hr-mcp"],
      "cwd": "C:/github/agents2/contoso-hr-agent",
      "env": {
        "PYTHONPATH": "C:/github/agents2/contoso-hr-agent/src"
      }
    }
  }
}
```

**IMPORTANT:** Update paths to match your system!

**Restart Claude Desktop completely (quit from system tray).**

**Verify connection:**

- Look for the tools icon in Claude's interface
- Test with: "List all evaluated candidates"
- Test with: "What does the HR policy say about certifications?"

---

## ChromaDB Knowledge Deep-Dive (15 minutes)

### How Knowledge Powers the Pipeline

**Draw on whiteboard:**

```text
sample_knowledge/             ChromaDB              policy_expert node
+-----------------+     +-----------------+     +-------------------+
| .pdf, .docx,    | --> | Azure embeddings| --> | query_hr_policy   |
| .pptx, .md      |     | text-embedding- |     | tool retrieves    |
| policy docs      |     | 3-large vectors |     | PolicyContext     |
+-----------------+     +-----------------+     +-------------------+
      |                                               |
  uv run hr-seed                              PolicyExpertAgent
  (vectorizer.py)                          uses context to evaluate
```

**Say:** "The knowledge base is the source of truth for HR policies. When PolicyExpertAgent needs to check a requirement, the query_hr_policy tool searches ChromaDB and returns the most relevant policy passages."

### Key Files

| File | Purpose |
| --- | --- |
| `knowledge/vectorizer.py` | Ingests policy docs -> Azure embeddings -> ChromaDB |
| `knowledge/retriever.py` | `query_policy_knowledge(question, k)` -> PolicyContext |
| `pipeline/tools.py` | `@tool query_hr_policy` wraps the retriever for CrewAI |
| `sample_knowledge/` | Source policy documents (.pdf, .docx, .pptx, .md) |

### Live Demo: Trace a Policy Query (5 minutes)

**In the web UI chat (<http://localhost:8080>):**

1. Ask Alex: "What certifications does a candidate need?"
2. Watch the server logs -- see the ChromaDB query and results
3. Show that Alex's answer is grounded in the actual policy documents

**In VSCode (set breakpoints):**

1. Open `knowledge/retriever.py`
2. Set breakpoint at `query_policy_knowledge()`
3. Chat with Alex again
4. Inspect the query embedding and ChromaDB results
5. Show how the `PolicyContext` is assembled

### How the Parallel Pipeline Uses Knowledge

**Key insight for learners:**

- `policy_expert` queries ChromaDB via `query_hr_policy` tool
- `resume_analyst` searches the web via `brave_web_search` tool
- These run **in parallel** -- neither waits for the other
- `decision_maker` receives both results and makes the final call

**Ask the class:** "Why is it better to run these in parallel rather than sequentially?"

---

## Vibe Coding: Add a Knowledge Feature (15 minutes)

### What is Vibe Coding?

**Say:** "Vibe coding is using AI to implement features conversationally. You describe WHAT you want, Claude Code figures out HOW."

**The approach:**

1. Describe the feature clearly
2. Let Claude Code explore and implement
3. Review, iterate, refine
4. Test the result

### The Feature: Knowledge Source Summary

**What we're building:** A new MCP tool or API endpoint that shows learners what's in the knowledge base -- what documents are indexed, how many chunks, what topics are covered.

### Step 1: Start Claude Code (3 minutes)

**Open Claude Code in the project:**

```bash
cd agents2/contoso-hr-agent
claude
```

**Initial exploration prompt:**

```text
I want to add a feature that summarizes what's in the ChromaDB knowledge base.
The goal is to:

1. List all documents that have been indexed
2. Show the total number of chunks
3. Show a sample of topics/content covered

First, explore the codebase and tell me:
- How is ChromaDB currently set up?
- What files handle the knowledge base?
- Where would this new feature fit?
```

**Watch Claude Code:**

- It will read `knowledge/vectorizer.py` and `knowledge/retriever.py`
- It will examine the ChromaDB collection setup
- It will suggest an approach

### Step 2: Implement with Claude Code (7 minutes)

**Prompt Claude Code:**

```text
Create a function in knowledge/retriever.py called get_knowledge_summary()
that returns:
- Total number of documents in ChromaDB
- List of unique source file names
- Sample of 5 random content snippets (first 100 chars each)

Then expose it as:
1. A new MCP tool called "knowledge_summary" in the MCP server
2. A new API endpoint GET /api/knowledge/summary in engine.py

Keep it simple and read-only.
```

**Review what Claude Code creates and iterate as needed.**

### Step 3: Test the Feature (5 minutes)

**Test via API:**

```bash
curl http://localhost:8080/api/knowledge/summary | python -m json.tool
```

**Test via MCP Inspector:**

1. Restart the MCP server: `uv run hr-mcp`
2. Open Inspector
3. Find "knowledge_summary" tool
4. Run it and inspect the results

**Test via Claude Desktop:**

- Ask: "What documents are in the HR knowledge base?"
- Claude should use the new tool to answer

---

## Wrap-Up (5 minutes)

### What We Accomplished

- Understood MCP architecture and our FastMCP 2 server
- Tested MCP tools with the MCP Inspector
- Connected MCP to Claude Desktop
- Deep-dived into ChromaDB knowledge retrieval
- Traced how policy_expert uses ChromaDB in the parallel pipeline
- Vibe coded a knowledge summary feature

### The Vibe Coding Process

1. **Describe** the feature at a high level
2. **Explore** the codebase with Claude
3. **Implement** incrementally with prompts
4. **Review** each change before continuing
5. **Test** the integrated feature

### What's Next (Hour 4)

- Azure deployment architecture
- Production best practices for AI agents
- Cost management and model routing
- Security, observability, and guardrails

### Quick Reference: MCP Commands

**Start MCP server:**

```bash
uv run hr-mcp              # FastMCP 2 on port 8081/sse
```

**Start MCP + Inspector:**

```bash
./scripts/start_mcp.sh     # Linux/macOS
.\scripts\start_mcp.ps1    # Windows
```

**Start HR engine (needed for full MCP functionality):**

```bash
uv run hr-engine            # FastAPI on port 8080
```

**Claude Desktop config location:**

```text
Windows: %APPDATA%\Claude\claude_desktop_config.json
macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
```

---

## Teaching Tips

### If MCP Server Won't Start

**Common issues:**

```bash
# Port 8081 already in use -- the server auto-kills it, but if not:
# Check what's using the port and kill it

# Missing dependencies
uv sync

# Check .env is configured
cat .env | grep AZURE_AI_FOUNDRY
```

### If Claude Desktop Doesn't Connect

**Checklist:**

1. Config file is valid JSON (no trailing commas)
2. Paths are correct for your system
3. Claude Desktop fully restarted (quit from system tray)
4. Check logs: `%APPDATA%\Claude\logs\mcp*.log`

### If ChromaDB Has No Data

**Re-seed the knowledge base:**

```bash
uv run hr-seed
```

**Verify:**

```bash
ls data/chroma/
# Should see ChromaDB files
```

### If Students Are Ahead

**Advanced challenges:**

1. Add a new MCP resource that returns the pipeline architecture as a Mermaid diagram
2. Add metadata filtering to knowledge queries (by document source)
3. Create a "compare candidates" MCP tool that fetches two candidates and compares them
4. Add a knowledge base health check that verifies embedding dimensions match

### Time Management

- If MCP setup takes too long: Skip Claude Desktop, use Inspector only
- If vibe coding is slow: Have pre-built code ready to show
- If running ahead: Add the advanced MCP tool challenges

---

## MCP Server Quick Reference

**Available tools:**

| Tool | Description |
| --- | --- |
| `get_candidate` | Fetch a specific candidate evaluation |
| `list_candidates` | List all evaluated candidates |
| `trigger_resume_evaluation` | Submit a resume for pipeline processing |
| `query_policy` | Query the HR policy knowledge base (ChromaDB) |

**Available resources:**

| URI | Description |
| --- | --- |
| `schema://candidate` | Candidate data model schema |
| `stats://evaluations` | Evaluation statistics |
| `samples://resumes` | Sample resume content |
| `config://settings` | Current app configuration |

**Available prompts:**

| Prompt | Description |
| --- | --- |
| `evaluate_resume` | Pre-built prompt for resume evaluation |
| `policy_query` | Pre-built prompt for policy questions |

---

**You got this! Vibe code with confidence.**
