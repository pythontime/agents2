# Contoso HR Agent — Code Walkthrough

A teaching guide for understanding how LangGraph and CrewAI work together in this app.
Use this alongside a live demo — open the files in the order listed below.

---

## Mental Model (Start Here)

> **LangGraph owns the flow. CrewAI owns the persona. Each node is one `Crew` with one agent and one task.**

The pipeline fans two specialist agents out in parallel, waits for both to finish, then hands their
combined output to a decision-maker for final reasoning. State flows as typed Pydantic models the
whole way.

---

## The 5 Files to Walk Through (In Order)

| # | File | Why Show It First |
|---|------|-------------------|
| 1 | [`pipeline/graph.py`](src/contoso_hr/pipeline/graph.py) | The skeleton — defines nodes, edges, and parallel fan-out/fan-in |
| 2 | [`pipeline/agents.py`](src/contoso_hr/pipeline/agents.py) | The workers — four CrewAI personas with distinct tool access |
| 3 | [`pipeline/tasks.py`](src/contoso_hr/pipeline/tasks.py) | The instructions — factory functions that inject live state into prompts |
| 4 | [`watcher/resume_watcher.py`](src/contoso_hr/watcher/resume_watcher.py) | The trigger — polls `data/incoming/` every 3 s, calls `graph.invoke()` |
| 5 | [`engine.py`](src/contoso_hr/engine.py) | The front door — `POST /api/upload` saves the file, returns 202, done |

---

## LangGraph Nodes

| Node | Type | What It Does |
|------|------|--------------|
| `intake` | Validation | Parses raw resume text into a `ResumeSubmission` Pydantic model |
| `policy_expert` | CrewAI crew | Queries ChromaDB — "does this candidate meet HR policy requirements?" |
| `resume_analyst` | CrewAI crew | Brave web search — scores skills fit, verifies certs, surfaces red flags |
| `decision_maker` | CrewAI crew | Receives both outputs, renders final disposition (no tools — pure reasoning) |
| `notify` | Assembly | Builds `EvaluationResult`, writes to SQLite + JSON, logs Rich summary |

---

## LangGraph Edges

| From | To | Type | Notes |
|------|----|------|-------|
| `intake` | `policy_expert` | Parallel fan-out | Both branches start simultaneously |
| `intake` | `resume_analyst` | Parallel fan-out | Both branches start simultaneously |
| `policy_expert` | `decision_maker` | Fan-in | Waits for both branches to complete |
| `resume_analyst` | `decision_maker` | Fan-in | Waits for both branches to complete |
| `decision_maker` | `notify` | Sequential | Runs after disposition is rendered |
| `notify` | `END` | Terminal | Writes result to SQLite and exits |

> **Key pattern:** Parallel nodes return **only the state keys they own** — never `{**state, ...}`.
> LangGraph merges the two partial updates at the fan-in point.

---

## CrewAI Agent Personas

| Agent | Persona | Tools | State It Produces |
|-------|---------|-------|-------------------|
| `ChatConciergeAgent` | "Alex" — friendly HR assistant | `query_hr_policy` (ChromaDB) | Chat reply via `/api/chat` |
| `PolicyExpertAgent` | HR Policy Expert | `query_hr_policy` (ChromaDB) | `PolicyContext` — compliance assessment |
| `ResumeAnalystAgent` | Sr. Talent Acquisition Specialist | `brave_web_search` (Brave API) | `CandidateEval` — scores, strengths, red flags |
| `DecisionMakerAgent` | Hiring Committee Chair | None (pure reasoning) | `HRDecision` — one of four dispositions |

### Four Dispositions

| Disposition | Score Range | Recommended Next Step |
|-------------|------------|----------------------|
| **Strong Match** | 80 – 100 | Schedule interview immediately |
| **Possible Match** | 55 – 79 | Schedule technical screen |
| **Needs Review** | 35 – 54 | Recruiter follow-up before deciding |
| **Not Qualified** | 0 – 34 | Decline with courtesy |

---

## Web UI — Three Pages

| Page | URL | Purpose |
|------|-----|---------|
| **Chat** | `/chat.html` | Talk to "Alex" the HR concierge; upload resumes via drag-and-drop |
| **Candidates** | `/candidates.html` | Grid of every evaluated candidate with scores and dispositions |
| **Pipeline Runs** | `/runs.html` | Side-by-side execution trace showing the parallel branches in real time |

---

## End-to-End Flow

```text
1. User uploads resume  →  POST /api/upload
                             └─ Saves to data/incoming/, returns 202

2. ResumeWatcher polls data/incoming/ every 3 seconds
   └─ Detects new file  →  process_resume_file()

3. graph.invoke(HRState)
   ├─ [intake]           Validate  →  ResumeSubmission
   ├─ [policy_expert]  ──┐  PARALLEL
   │   query ChromaDB    │          →  PolicyContext
   ├─ [resume_analyst] ──┘  PARALLEL
   │   Brave web search             →  CandidateEval
   ├─ [decision_maker]  FAN-IN
   │   pure reasoning               →  HRDecision
   └─ [notify]          Assemble    →  EvaluationResult

4. Result written to:
   - data/hr.db  (SQLite)
   - data/outgoing/{candidate_id}.json

5. /candidates.html auto-refreshes  →  displays score + disposition
```

---

## Best Architecture Diagram

Open **`README.md`** and scroll to **Diagram B — Evaluation Pipeline** (the sequence diagram).

It shows the `par` block where `policy_expert` and `resume_analyst` fire concurrently,
and the fan-in at `decision_maker` — the two concepts that are hardest to grasp from code alone.
