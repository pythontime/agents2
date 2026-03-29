# Build Production-Ready AI Agents — Course Plan

**O'Reilly Live Learning | 4 × 50-minute segments + 10-minute breaks**

---

## Segment 1 — Understanding Agents at Depth (50 min)

**Theme:** What makes an agent an *agent*, and how do the pieces fit together?

- [ ] Agent anatomy: perception → reasoning → memory → action loop
- [ ] Token limits, context windows, and why they constrain agent design
- [ ] Memory types: in-context, external (vector/SQL), episodic, semantic
- [ ] Tool use and function calling — how agents reach outside the LLM
- [ ] MCP (Model Context Protocol) — what it is and why it matters
- [ ] Agent patterns: ReAct, plan-and-execute, multi-agent orchestration
- [ ] **Demo:** Claude Code custom agents — show a subagent being dispatched
- [ ] **Demo:** Claude Code skills — invoke a skill, show the prompt expansion
- [ ] **Demo:** Claude Code CLAUDE.md / agent context files
- [ ] Q&A / break

---

## Segment 2 — Low-Code Agent Deep-Dive (50 min)

**Theme:** Copilot Studio as an opinionated, visual agent runtime

- [ ] Copilot Studio orientation: topics, actions, knowledge, variables
- [ ] Build a Contoso HR Agent in Copilot Studio (no-code version)
  - [ ] Add HR policy knowledge source (SharePoint / URL)
  - [ ] Create a resume intake topic with triggers and entities
  - [ ] Wire a connector action (e.g. send email on decision)
  - [ ] Add generative answers node grounded in policy docs
- [ ] Global variables and conversation state
- [ ] Adaptive Cards for structured output
- [ ] Publish to Teams channel — end-to-end demo
- [ ] Compare low-code vs code-first: when to use each
- [ ] Q&A / break

---

## Segment 3 — Code-First Agentic AI (50 min)

**Theme:** The Contoso HR Agent — LangGraph + CrewAI in production patterns

- [ ] Repo tour: `contoso-hr-agent/` structure, `uv` workflow, `.env` setup
- [ ] LangGraph fundamentals: StateGraph, nodes, edges, checkpointing
- [ ] **Key demo:** Parallel fan-out — `policy_expert` ‖ `resume_analyst` run concurrently
  - [ ] Show the graph wiring (`add_edge` fan-out / fan-in)
  - [ ] Show partial state returns — why parallel nodes can't do `{**state, ...}`
- [ ] CrewAI agents: persona, tools, `Crew.kickoff()` per node
- [ ] ChromaDB RAG: vectorizer → retriever → `query_hr_policy` tool
- [ ] Chat memory: localStorage + server JSON + cross-session context injection
- [ ] **Live run:** Drop a resume → watch all five pipeline nodes fire in terminal
- [ ] **Pipeline Runs page (`runs.html`):** walk through the trace together
- [ ] MCP server preview: `uv run hr-mcp`, hit tools in MCP Inspector
- [ ] Q&A / break

---

## Segment 4 — Deployment, Monitoring, Optimization (50 min)

**Theme:** Getting agents to production and keeping them there

- [ ] Azure deployment patterns for agents (ACA, App Service, AKS)
- [ ] Azure AI Foundry: model deployment, endpoint management, API versioning
- [ ] Observability: LangSmith tracing, Application Insights, structured logging
- [ ] MCP in the real world
  - [ ] Connect MCP server to Claude Code (`claude_desktop_config.json`)
  - [ ] Connect MCP server to GitHub Copilot in VS Code
  - [ ] MCP Inspector for live tool testing and debugging
- [ ] Cost and token optimization: model routing, caching, prompt compression
- [ ] Security: secret management (Key Vault), input validation, PII handling
- [ ] Evaluation and regression testing for agent outputs
- [ ] Shavings sweep: common failure modes, retry patterns, graceful degradation
- [ ] Resources, next steps, community links
- [ ] Final Q&A
