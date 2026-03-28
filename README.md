# Build Production-Ready AI Agents

<p align="center">
   <img src="images/cover.png" alt="Build Production-Ready AI Agents cover" width="360">
</p>

**O'Reilly Live Learning Course** | 4 Hours | LangGraph - CrewAI - MCP - Azure AI Foundry

[![Website TechTrainerTim.com](https://img.shields.io/badge/Website-TechTrainerTim.com-0a66c2)](https://techtrainertim.com)
[![LinkedIn timothywarner](https://img.shields.io/badge/LinkedIn-timothywarner-0a66c2?logo=linkedin)](https://www.linkedin.com/in/timothywarner/)
[![GitHub timothywarner-org](https://img.shields.io/badge/GitHub-timothywarner--org-181717?logo=github)](https://github.com/timothywarner-org)
[![O'Reilly Author Page](https://img.shields.io/badge/O'Reilly-Author%20Page-cf2f1d)](https://learning.oreilly.com/search/?query=Tim%20Warner)

**Contact:** [Website](https://techtrainertim.com) | [LinkedIn](https://www.linkedin.com/in/timothywarner/) | [GitHub](https://github.com/timothywarner-org) | [O'Reilly](https://learning.oreilly.com/search/?query=Tim%20Warner)

---

## Course Overview

A 4-hour hands-on workshop teaching you how to build, orchestrate, and deploy multi-agent AI systems using real production patterns. The primary demo is the **Contoso HR Agent** -- an automated resume screening and HR policy Q&A system that showcases five core agent capabilities:

| Pillar | What it demonstrates |
|--------|---------------------|
| **(a) Interactive chat** | Web chat UI + FastAPI `/api/chat` backed by Azure AI Foundry |
| **(b) Event-driven autonomy** | `ResumeWatcher` polls `data/incoming/` -- drop a resume, pipeline runs automatically |
| **(c) Memory/state persistence** | LangGraph `SqliteSaver` checkpoints + SQLite candidate store |
| **(d) LLM reasoning** | LangGraph StateGraph + 3 CrewAI agents (PolicyExpert, ResumeAnalyst, DecisionMaker) |
| **(e) MCP tool calling** | FastMCP 2 server (SSE) + Brave Search API tool inside ResumeAnalyst agent |

### Tech Stack

- **Python 3.11+** -- primary language
- **LangGraph** -- StateGraph orchestration, state machine, checkpoints
- **CrewAI** -- agent persona framework (PolicyExpert, ResumeAnalyst, DecisionMaker)
- **Azure AI Foundry** -- LLM (GPT-4o) and embeddings (text-embedding-3-large)
- **FastMCP 2** -- Model Context Protocol server (SSE transport)
- **ChromaDB** -- vector store for HR policy RAG
- **FastAPI** -- web server and REST API

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/timothywarner-org/agents2.git
cd agents2/contoso-hr-agent

# 2. Run setup (requires uv package manager)
.\scripts\setup.ps1         # Windows PowerShell
./scripts/setup.sh          # Linux/macOS

# 3. Configure .env
# Set your Azure AI Foundry credentials:
#   AZURE_AI_FOUNDRY_ENDPOINT, AZURE_AI_FOUNDRY_KEY,
#   AZURE_AI_FOUNDRY_CHAT_MODEL, AZURE_AI_FOUNDRY_EMBEDDING_MODEL

# 4. Start the application
.\scripts\start.ps1         # Windows PowerShell
./scripts/start.sh          # Linux/macOS

# 5. Open the chat UI
# http://localhost:8080/chat.html
```

See [contoso-hr-agent/README.md](contoso-hr-agent/README.md) for the full demo walkthrough and project details.

---

## Project Structure

```
agents2/
├── README.md                      # <- You are here (course outline)
├── contoso-hr-agent/              # <- Primary demo project
│   ├── src/contoso_hr/            # Source code
│   │   ├── pipeline/              # LangGraph + CrewAI orchestration
│   │   ├── knowledge/             # ChromaDB vectorization + retrieval
│   │   ├── memory/                # SQLite store + LangGraph checkpoints
│   │   ├── mcp_server/            # FastMCP 2 (SSE, port 8081)
│   │   ├── watcher/               # Resume file watcher
│   │   └── engine.py              # FastAPI server (port 8080)
│   ├── web/                       # HTML/JS/CSS frontend
│   ├── sample_resumes/            # Trainer candidate resumes
│   ├── sample_knowledge/          # HR policy docs
│   ├── scripts/                   # Setup and launch scripts
│   └── tests/                     # pytest tests
├── oreilly-agent-mvp/             # Legacy reference (issue triage pipeline)
├── docs/                          # Course materials and supporting assets
└── images/                        # Course images
```

> **Note:** `oreilly-agent-mvp/` is retained as reference material from an earlier iteration of the course. It is not the primary demo. All learner-facing work should use `contoso-hr-agent/`.

---

## Course Flow (4 Hours)

### Hour 1: Agent Fundamentals & Existing Tools (0:00-1:00)

**What are AI Agents, Really?**
- Definition: LLMs + Tools + Memory + Autonomy
- Agents vs. Chatbots vs. Assistants (clearing the confusion)
- When to use agents (and when NOT to)
- Real-world use cases that actually make sense

**Hands-On: Copilot Studio (20 minutes)**
- Creating a simple agent in Copilot Studio
- Adding skills and topics
- Testing conversational flow
- Publishing and monitoring

**Hands-On: Claude Code (20 minutes)**
- Setting up Claude for Desktop
- Writing prompts that work
- Using Model Context Protocol (MCP) for GitHub
- File operations, code generation, debugging

**Key Takeaway:** You don't need to build from scratch. Use existing tools when they fit.

---

### Hour 2: Contoso HR Agent - Architecture & Setup (1:00-2:00)

**The Big Picture**
- Demo: Watch the full pipeline run (Resume upload -> PolicyExpert -> ResumeAnalyst -> DecisionMaker -> Result)
- Architecture walkthrough: Why 3 agents? Why these roles?
- LangGraph vs. CrewAI: When to use which framework

**Hands-On: Get It Running (30 minutes)**
- Clone the repo, run setup
- Configure Azure AI Foundry credentials
- Start the engine and watcher
- Upload a sample resume from `sample_resumes/`
- View results on the candidates page

**Code Walkthrough (15 minutes)**
- `models.py`: Data flowing through the system
- `config.py`: Azure AI Foundry configuration
- `pipeline/graph.py`: The LangGraph StateGraph

**Key Takeaway:** Understand the flow before diving into code.

---

### Hour 3: Agent Roles & Prompt Engineering (2:00-3:00)

**Deep Dive: The Three Agents**
- **PolicyExpert:** ChromaDB RAG against HR policy documents
- **ResumeAnalyst:** Skills evaluation with Brave Search verification
- **DecisionMaker:** Final advance/hold/reject reasoning

**Hands-On: Prompt Dissection (20 minutes)**
- Open `pipeline/prompts.py`
- Read the PolicyExpert prompt together
- Identify: System prompt vs. task description
- Spot the output structure requirements
- See how context flows between agents

**Hands-On: Modify a Prompt (25 minutes)**
- Pick an agent (PolicyExpert, ResumeAnalyst, or DecisionMaker)
- Change the evaluation criteria or tone
- Re-run the pipeline with a sample resume
- Compare outputs
- Discussion: What changed?

**Hands-On: MCP Integration (15 minutes)**
- Start the MCP server
- Use MCP Inspector to call `list_candidates`, `query_policy`, `trigger_resume_evaluation`
- See how MCP exposes the pipeline to external AI tools

**Key Takeaway:** Prompts are code. Small changes = big impacts.

---

### Hour 4: Orchestration & Taking It Home (3:00-4:00)

**LangGraph Orchestration**
- State management: HRState TypedDict flows between nodes
- Nodes vs. edges (it's just a graph!)
- SqliteSaver checkpoints: memory and replay
- Error handling: What happens when agents fail?

**CrewAI Agent Patterns**
- When would you use CrewAI vs. raw LangGraph?
- One Crew per node pattern
- Agent collaboration and tool binding

**Hands-On: Extension Ideas (30 minutes)**

*Pick ONE to try:*

1. **Add a 4th agent** (InterviewScheduler that proposes calendar slots)
2. **Add a new tool** (Microsoft Graph for email notifications)
3. **Upgrade the knowledge store** (Azure AI Search instead of ChromaDB)
4. **New input source** (connect to an ATS or read resumes from SharePoint)

**Production Considerations (10 minutes)**
- Cost tracking (Azure AI Foundry pricing)
- Observability (logs, traces, metrics)
- Rate limiting and retries
- Security (secrets, data privacy)
- Testing agent systems

**Wrap-Up: What's Next?**
- Resources: LangGraph docs, CrewAI tutorials, Azure AI Foundry docs
- Community: Where to get help
- Your homework: Deploy this to production

---

## Prerequisites

**You Should Have:**
- Basic Python experience (if/else, functions, imports)
- Used an LLM before (ChatGPT, Claude, etc.)
- Comfortable with terminal/command line
- Git basics (clone, commit, push)

**You DON'T Need:**
- Deep Python expertise
- LangGraph or CrewAI experience
- Machine learning knowledge
- Azure experience (we'll walk through setup)

**Required Tools:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- VS Code (recommended) or any editor
- Git
- Azure AI Foundry account with a deployed chat + embedding model
- Optional: Brave Search API key (for ResumeAnalyst web verification)
- Optional: Node.js (for MCP Inspector)

---

## Learning Outcomes

By the end of this course, you'll be able to:

- **Explain** what AI agents are and when to use them
- **Use** Copilot Studio and Claude Code effectively
- **Build** a multi-agent system with clear roles (PolicyExpert, ResumeAnalyst, DecisionMaker)
- **Orchestrate** agents using LangGraph with CrewAI personas
- **Write** effective prompts for agent personas
- **Integrate** tools via MCP and vector search via ChromaDB
- **Deploy** event-driven agent workflows with file watchers and web UIs
- **Extend** the system for your own use cases

---

## Resources

**Documentation:**
- [Contoso HR Agent docs](contoso-hr-agent/README.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-studio/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

**Code Examples:**
- `contoso-hr-agent/sample_resumes/` -- Sample trainer resumes
- `contoso-hr-agent/sample_knowledge/` -- HR policy documents
- `contoso-hr-agent/src/contoso_hr/pipeline/` -- Agent code

**Community:**
- Course Slack: (link provided in class)
- GitHub Issues: [Report bugs or ask questions](https://github.com/timothywarner-org/agents2/issues)

---

## Troubleshooting

**"Setup failed" or "uv sync errors"**
- Make sure Python 3.11+ is installed: `python --version`
- Install uv: `pip install uv` or see [uv docs](https://docs.astral.sh/uv/)
- Run `uv venv && uv sync` manually from `contoso-hr-agent/`

**"Azure AI Foundry key not working"**
- Check for typos in `.env` file
- Verify endpoint format: `https://YOUR-RESOURCE.openai.azure.com/`
- Ensure your deployment names match `AZURE_AI_FOUNDRY_CHAT_MODEL` and `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`

**"Port already in use"**
- The start scripts automatically kill ports 8080 and 8081 before starting
- If issues persist, manually kill the process using the port

**See full troubleshooting guide:** [contoso-hr-agent/README.md](contoso-hr-agent/README.md)

---

## License & Usage

MIT License - Feel free to use this code in your own projects!

**Course Materials:** (c) 2026 Tim Warner / O'Reilly Media
**Code:** Open source, use freely

---

## About the Instructor

**Tim Warner** teaches cloud, DevOps, and AI at O'Reilly, Pluralsight, and LinkedIn Learning.

- [TechTrainerTim.com](https://TechTrainerTim.com)
- [LinkedIn](https://linkedin.com/in/timothywarner)
- [GitHub](https://github.com/timothywarner-org)
