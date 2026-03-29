# Hour 2 Teaching Guide: Run, Test, and Debug the Parallel Pipeline

**Goal:** Students run the full HR agent pipeline, see parallel subagent execution live, understand testing, and master VSCode debugging.

**Time:** 60 minutes

**Active Project:** `contoso-hr-agent/` (the Contoso HR Agent for MCT resume screening)

---

## Opening (3 minutes)

**What We're Doing This Hour:**

1. Run the complete HR pipeline with **parallel subagent execution**
2. See the Pipeline Runs page (runs.html) visualizing parallel branches live
3. Chat with the HR concierge agent (Alex) via the web UI
4. Write and run tests
5. Master VSCode debugging with breakpoints

**Key Message:** "You can't fix what you can't see. The Pipeline Runs page lets you watch each node's output, parallel branches, scores, and reasoning in real time."

---

## Run the Pipeline (15 minutes)

### Setup Verification (5 minutes)

**Everyone check their environment:**

```bash
cd agents2/contoso-hr-agent

# Check Python
python --version  # Should be 3.11+

# First-time setup (creates venv, installs deps, seeds ChromaDB)
uv venv && uv sync && uv run hr-seed

# Verify .env
cat .env | grep -E "AZURE_AI_FOUNDRY"
# Should show your endpoint, key, and model names
```

**Required env vars (from .env.example):**

- `AZURE_AI_FOUNDRY_ENDPOINT`
- `AZURE_AI_FOUNDRY_KEY`
- `AZURE_AI_FOUNDRY_CHAT_MODEL`
- `AZURE_AI_FOUNDRY_EMBEDDING_MODEL`

### First Pipeline Run (10 minutes)

**Start the FastAPI engine:**

```bash
uv run hr-engine
# Starts on http://localhost:8080
```

**Open the web UI in your browser:**

- **Chat page:** <http://localhost:8080> (chat.html) -- talk to Alex the HR concierge, upload resumes
- **Candidates page:** <http://localhost:8080/candidates.html> -- results grid of evaluated candidates
- **Pipeline Runs page:** <http://localhost:8080/runs.html> -- live pipeline execution trace

**Demo: Upload a resume via the Chat page:**

1. Open http://localhost:8080
2. Click the upload button or drop a resume file (.txt, .md, .pdf, .docx)
3. Watch the pipeline execute

**While it runs, narrate the Pipeline Runs page (runs.html):**

- "The intake node validates the ResumeSubmission..."
- "Now watch -- policy_expert and resume_analyst start **at the same time** (parallel fan-out)..."
- "PolicyExpertAgent queries ChromaDB for HR policy context..."
- "ResumeAnalystAgent optionally searches the web via Brave Search..."
- "Both complete, and decision_maker receives merged results (fan-in)..."
- "DecisionMakerAgent renders the final disposition..."
- "The notify node writes the EvaluationResult"

**Show the output on the Candidates page:**

- Candidate name, disposition (Strong Match / Possible Match / Needs Review / Not Qualified)
- Skills match score, experience score
- Strengths, red flags, reasoning, next steps

### Understanding the Parallel Pipeline

**This is the key teaching demo. Draw on whiteboard:**

```text
                    +---> [policy_expert] ---+
                    |     (ChromaDB query)   |
[intake] --> fan-out                         fan-in --> [decision_maker] --> [notify]
                    |                        |
                    +---> [resume_analyst] --+
                          (Brave Search)
```

**LangGraph code that makes this happen:**

```python
# pipeline/graph.py
builder.add_edge("intake", "policy_expert")      # fan-out edge 1
builder.add_edge("intake", "resume_analyst")      # fan-out edge 2
builder.add_edge("policy_expert", "decision_maker")   # fan-in edge 1
builder.add_edge("resume_analyst", "decision_maker")   # fan-in edge 2
```

**Say:** "This is the subagent pattern. LangGraph owns the routing and state. CrewAI owns the persona execution inside each node. The two frameworks are fully coupled -- each crew node creates a Crew with one agent and one task, then calls crew.kickoff()."

### The Four Dispositions

| Disposition | Meaning |
| --- | --- |
| **Strong Match** | Candidate meets or exceeds all criteria |
| **Possible Match** | Candidate has potential but gaps exist |
| **Needs Review** | Requires human review for edge cases |
| **Not Qualified** | Candidate does not meet minimum criteria |

---

## Understanding the Architecture (10 minutes)

### Pipeline State Flow (HRState TypedDict)

**Draw on whiteboard:**

```text
+-------------------+
| HRState           |
+-------------------+
| session_id        |
| resume_submission | <-- intake fills this (validated ResumeSubmission)
| policy_context    | <-- policy_expert fills this (PolicyContext from ChromaDB)
| candidate_eval    | <-- resume_analyst fills this (CandidateEval with scores)
| hr_decision       | <-- decision_maker fills this (HRDecision with disposition)
| evaluation_result | <-- notify fills this (final EvaluationResult)
+-------------------+
```

**Key insight:** "State is a bucket that passes from node to node. Each agent reads what it needs and adds its output. The parallel nodes (policy_expert and resume_analyst) write to different keys, so there are no conflicts."

### The Data Model Chain

```text
ResumeSubmission (input)
  -> PolicyContext     (ChromaDB retrieval result)
  -> CandidateEval    (skills_match_score, experience_score, strengths, red_flags)
  -> HRDecision       (disposition, reasoning, next_steps, overall_score)
  -> EvaluationResult (final -- written to SQLite + served by API)
```

### The Four CrewAI Agents

| Agent | Pipeline Node | Tools | Purpose |
| --- | --- | --- | --- |
| ChatConciergeAgent ("Alex") | /api/chat | query_hr_policy | Interactive HR Q&A via web UI |
| PolicyExpertAgent | policy_expert | query_hr_policy | Assesses resume against HR policy (ChromaDB) |
| ResumeAnalystAgent | resume_analyst | brave_web_search | Scores candidate fit, optional web research |
| DecisionMakerAgent | decision_maker | none (pure reasoning) | Renders final disposition |

### Chat Features

**The Chat page (chat.html) includes:**

- Session management (create new, switch sessions)
- Past sessions panel (sidebar listing previous conversations)
- 6 suggestion buttons for common HR questions
- Past session context injected into the concierge agent prompt (last 20 turns)
- Two-layer memory: `localStorage` in browser + JSON files in `data/chat_sessions/{session_id}.json`

---

## Running Tests (12 minutes)

### Test Suite Overview (3 minutes)

**Show the test structure:**

```bash
ls tests/
# tests/
# +-- test_models.py        # Pydantic model validation
# +-- test_config.py         # Configuration tests
# +-- conftest.py            # Shared fixtures
```

**Say:** "Tests verify contracts. When you change code, tests catch regressions."

### Run All Tests (4 minutes)

**Basic test run:**

```bash
uv run pytest tests/ -v
```

**With coverage:**

```bash
uv run pytest --cov=contoso_hr
```

**Lint and format check:**

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Run Specific Tests (5 minutes)

**Single file:**

```bash
uv run pytest tests/test_models.py -v
```

**Single test function:**

```bash
uv run pytest tests/test_models.py::test_resume_submission_validation -v
```

**Pattern matching:**

```bash
uv run pytest -k "policy" -v  # All tests with "policy" in name
```

**Hands-on:** "Everyone run the model tests and verify they pass."

---

## VSCode Debugging (20 minutes)

### Open VSCode Correctly (2 minutes)

**IMPORTANT:** Open the `agents2/` folder, NOT `contoso-hr-agent/`.

```bash
code c:/github/agents2
```

**Why?** The launch configurations and PYTHONPATH are set relative to this root.

### Available Debug Configurations (3 minutes)

**Press F5 and see the dropdown:**

| Config | Purpose | Best For |
| --- | --- | --- |
| HR Engine | FastAPI on port 8080 | Testing the full web UI |
| Folder Watcher | Event-driven resume processing | Testing file drop automation |
| MCP Server | FastMCP 2 on port 8081 | Testing MCP tools/resources |
| Run Tests (All) | All pytest tests | TDD workflow |
| Seed Knowledge | Re-seed ChromaDB | Testing knowledge ingestion |

**Say:** "Start with 'HR Engine' -- it gives you the full web UI with chat, candidates, and pipeline runs."

### Essential Keyboard Shortcuts (2 minutes)

| Key | Action |
| --- | --- |
| **F5** | Start debugging / Continue |
| **F9** | Toggle breakpoint |
| **F10** | Step Over (next line) |
| **F11** | Step Into (enter function) |
| **Shift+F11** | Step Out (exit function) |
| **Ctrl+Shift+Y** | Open Debug Console |

### Demo: Step Through the Parallel Pipeline (8 minutes)

**Setup:**

1. Open VSCode in `agents2/`
2. Open `contoso-hr-agent/src/contoso_hr/pipeline/graph.py`
3. Set breakpoints at:
   - Inside `intake_node()` after validation
   - Inside `policy_expert_crew_node()` after `crew.kickoff()`
   - Inside `resume_analyst_crew_node()` after `crew.kickoff()`
   - Inside `decision_maker_crew_node()` after `crew.kickoff()`

**Run:**

1. Press F5, select "HR Engine"
2. Upload a resume via <http://localhost:8080>
3. When it pauses at intake_node:
   - **Variables pane:** Expand `state` to see `resume_submission`
   - **Debug Console:** Type `state["resume_submission"]`
   - Press F5 to continue

4. When it pauses at policy_expert_crew_node:
   - **Check:** `state["resume_submission"]` exists
   - **Debug Console:** Inspect the PolicyContext being built
   - Press F5

5. When it pauses at decision_maker_crew_node:
   - **Check:** Both `policy_context` and `candidate_eval` exist
   - **Debug Console:** `state["candidate_eval"]["skills_match_score"]`

**Key insight:** "Watch state keys grow through the pipeline. In production, the runs.html page shows all of this live."

### Hands-On: Debug the Chat Concierge (5 minutes)

**Set breakpoint in the chat endpoint:**

Open `contoso-hr-agent/src/contoso_hr/engine.py`

Set breakpoint in the `/api/chat` handler.

**Run with "HR Engine" config:**

When it stops:

- Inspect the incoming chat message
- See how session context (last 20 turns) is included
- Watch the ChatConciergeAgent ("Alex") query ChromaDB via `query_hr_policy`

**Debug Console commands:**

```python
request.message
request.session_id
```

---

## Common Debugging Scenarios (5 minutes)

### Scenario 1: "Why did a candidate get 'Not Qualified'?"

1. Open runs.html and find the pipeline run
2. Check policy_expert output -- what policies were matched?
3. Check resume_analyst output -- what scores were assigned?
4. Check decision_maker reasoning -- what drove the disposition?
5. Set breakpoints in the crew nodes to inspect intermediate state

### Scenario 2: "ChromaDB returns no results"

1. Verify knowledge base is seeded: `uv run hr-seed`
2. Check `data/chroma/` directory exists and has files
3. Set breakpoint in `knowledge/retriever.py` at `query_policy_knowledge()`
4. Inspect the embedding query and results

### Scenario 3: "Chat agent doesn't remember context"

1. Check `data/chat_sessions/{session_id}.json` exists
2. Verify `localStorage` in browser dev tools
3. Set breakpoint in `/api/chat` to inspect the transcript context
4. Confirm last 20 turns are being injected into the task prompt

### Scenario 4: "Pipeline hangs at a crew node"

1. Enable "Break on Exception" (Debug sidebar -> Breakpoints)
2. Run the pipeline
3. When it hangs, press pause button
4. Check Call Stack to see where it's stuck
5. Often: Azure AI Foundry timeout or rate limiting

---

## Wrap-Up (5 minutes)

### What We Accomplished

- Ran the full parallel HR pipeline (intake -> [policy_expert || resume_analyst] -> decision_maker -> notify)
- Saw live pipeline execution on runs.html with parallel branches visualized
- Chatted with the HR concierge agent (Alex) via the web UI
- Understood the data model chain (ResumeSubmission -> EvaluationResult)
- Ran tests with pytest
- Mastered VSCode debugging with breakpoints

### What's Next (Hour 3)

- Configure the MCP server (FastMCP 2) for external integration
- Test MCP tools with the MCP Inspector
- Vibe code a new feature with Claude Code
- Deep dive into ChromaDB knowledge retrieval

### Quick Reference Card

**Start the engine:**

```bash
uv run hr-engine          # FastAPI on http://localhost:8080
```

**Web pages:**

- <http://localhost:8080> -- Chat with Alex + upload resumes
- <http://localhost:8080/candidates.html> -- Results grid
- <http://localhost:8080/runs.html> -- Pipeline Runs trace (parallel branches)

**Run tests:**

```bash
uv run pytest tests/ -v
uv run pytest --cov=contoso_hr
```

**Debug in VSCode:**

1. F5 -> Select config
2. F9 -> Toggle breakpoint
3. F10 -> Step over
4. Ctrl+Shift+Y -> Debug console

**Inspect state:**

```python
state.keys()
state["resume_submission"]
state["policy_context"]
state["candidate_eval"]["skills_match_score"]
state["hr_decision"]["disposition"]
```

---

## Teaching Tips

### If VSCode Debugging Doesn't Work

**Check:**

1. Opened `agents2/` not `contoso-hr-agent/`
2. Python extension installed
3. Correct Python interpreter selected (bottom status bar)
4. `.venv` activated

**Fix PYTHONPATH issues:**

```bash
# In terminal before launching VSCode
export PYTHONPATH=$PWD/contoso-hr-agent/src
code .
```

### If Tests Fail

**Common issues:**

1. Missing dependencies: `uv sync`
2. Missing `.env` file: Copy from `.env.example`
3. ChromaDB not seeded: `uv run hr-seed`
4. API key issues: Check for spaces/quotes in `.env`

### If Pipeline Hangs

**Causes:**

- Azure AI Foundry rate limiting (wait 60 seconds)
- Network issues (check connectivity)
- Model deployment not ready

### Highlight the Parallel Execution

**This is the key teaching moment.** When showing runs.html:

- Point out that policy_expert and resume_analyst start at the same time
- Show the timestamps -- they overlap, proving concurrency
- Explain fan-out (one node to many) and fan-in (many nodes to one)
- Ask: "What would happen if we added a fifth agent in parallel?"

### Time Management

- If setup takes too long: Demo on your screen
- If students are ahead: Challenge them to add a 5th agent to the pipeline
- If debugging is confusing: Focus on just F5/F10/F9

---

## Advanced: Conditional Breakpoints

**Right-click breakpoint -> Edit Breakpoint -> Expression:**

```python
# Only stop if score is low
state["candidate_eval"]["skills_match_score"] < 50

# Only stop on specific disposition
state["hr_decision"]["disposition"] == "Not Qualified"

# Only stop for errors
state.get("error") is not None
```

---

## File Reference

| File | Purpose |
| --- | --- |
| `pipeline/graph.py` | LangGraph StateGraph, HRState TypedDict, all 5 node functions, `create_hr_graph()` |
| `pipeline/agents.py` | ChatConciergeAgent, PolicyExpertAgent, ResumeAnalystAgent, DecisionMakerAgent (CrewAI) |
| `pipeline/tasks.py` | CrewAI Task factories (inject prior state into task descriptions) |
| `pipeline/tools.py` | `@tool query_hr_policy` (ChromaDB) + `@tool brave_web_search` (Brave API) |
| `pipeline/prompts.py` | Agent system prompts |
| `models.py` | Pydantic v2 model chain: ResumeSubmission -> PolicyContext -> CandidateEval -> HRDecision -> EvaluationResult |
| `config.py` | Config dataclass, Azure AI Foundry LLM/embeddings factory |
| `engine.py` | FastAPI: /api/chat, /api/upload, /api/candidates, /api/stats, /api/chat/history/{id} |
| `knowledge/retriever.py` | `query_policy_knowledge(question, k)` -> PolicyContext |
| `knowledge/vectorizer.py` | Ingest policy docs -> Azure embeddings -> ChromaDB |

---

**You got this! Debug like you mean it.**
