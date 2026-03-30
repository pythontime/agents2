# LangGraph Patterns — Contoso HR Agent

Reference for `src/contoso_hr/pipeline/graph.py` and `memory/checkpoints.py`.

---

## HRState TypedDict

The canonical state definition. Every key written by any node must be declared here.

```python
class HRState(TypedDict):
    # Input
    resume_text: str
    session_id: str
    run_id: str
    start_time: str

    # Parallel fan-out outputs (each written by exactly one node)
    policy_context: Optional[PolicyContext]
    policy_context_summary: Optional[str]
    compliance_notes: Optional[str]
    recommended_level: Optional[str]
    compensation_band: Optional[str]

    candidate_eval: Optional[CandidateEval]
    skills_match_score: Optional[float]
    experience_score: Optional[float]
    strengths: Optional[list[str]]
    red_flags: Optional[list[str]]
    recommended_role: Optional[str]
    web_research_notes: Optional[str]

    # Fan-in output
    hr_decision: Optional[HRDecision]

    # Final
    result: Optional[EvaluationResult]
    error: Optional[str]
```

### Adding a New Field

When a node needs to write a new field:
1. Add to `HRState` TypedDict with appropriate `Optional[T]` type
2. Update the relevant Pydantic model in `models.py` if it surfaces in the API
3. Add to `EvaluationResult` only if it belongs in the persisted output
4. Update `sqlite_store.py` if it needs to be queryable from SQLite

---

## Parallel Fan-Out / Fan-In

The most common source of bugs. Understand this deeply.

### Topology

```
[intake]
    |
    +---> [policy_expert]  (concurrent)
    +---> [resume_analyst] (concurrent)
              |
              v
        [decision_maker]  (waits for both)
              |
              v
          [notify]
```

### Graph Wiring

```python
graph.add_edge(START, "intake")
graph.add_edge("intake", "policy_expert")
graph.add_edge("intake", "resume_analyst")
graph.add_edge("policy_expert", "decision_maker")
graph.add_edge("resume_analyst", "decision_maker")
graph.add_edge("decision_maker", "notify")
graph.add_edge("notify", END)
```

LangGraph automatically holds `decision_maker` until BOTH upstream nodes have returned.

### CRITICAL: Partial State Returns

```python
# ✅ CORRECT — policy_expert returns only its keys
def policy_expert_node(state: HRState) -> dict:
    # ... run crew ...
    return {
        "policy_context": ctx,
        "policy_context_summary": summary,
        "compliance_notes": notes,
    }

# ❌ WRONG — spreading full state creates race condition with resume_analyst
def policy_expert_node(state: HRState) -> dict:
    return {
        **state,                     # BUG: overwrites resume_analyst output
        "policy_context": ctx,
    }
```

LangGraph merges partial dicts from concurrent nodes. A full `{**state, ...}` spread
in either parallel node will clobber the other node's output, because whichever
finishes last wins.

### Handling PolicyContext in ResumeAnalyst

`resume_analyst` may run before `policy_expert` completes. The task factory handles this:

```python
# tasks.py — ResumeAnalystTask accepts Optional[PolicyContext]
def ResumeAnalystTask(
    state: HRState,
    policy_context: Optional[PolicyContext] = None,  # May be None during parallel exec
) -> Task:
    policy_note = (
        f"Policy context: {policy_context.summary}"
        if policy_context else
        "Policy context not yet available — proceed with resume analysis only."
    )
    # Inject into task description...
```

---

## Node Functions

Each node follows this structure:

```python
def intake_node(state: HRState) -> dict:
    """Validate resume input and initialize run metadata."""
    try:
        submission = ResumeSubmission(
            resume_text=state["resume_text"],
            session_id=state["session_id"],
        )
        return {
            "run_id": str(uuid4()),
            "start_time": datetime.utcnow().isoformat(),
            # Only keys this node owns
        }
    except ValidationError as e:
        return {"error": f"Invalid resume submission: {e}"}
```

### Node Ownership Map

| Node | Writes These Keys |
|------|-------------------|
| `intake` | `run_id`, `start_time` (validates `resume_text`, `session_id`) |
| `policy_expert` | `policy_context`, `policy_context_summary`, `compliance_notes`, `recommended_level`, `compensation_band` |
| `resume_analyst` | `candidate_eval`, `skills_match_score`, `experience_score`, `strengths`, `red_flags`, `recommended_role`, `web_research_notes` |
| `decision_maker` | `hr_decision` |
| `notify` | `result` |

---

## SqliteSaver Checkpoints

```python
# memory/checkpoints.py
def get_checkpointer() -> SqliteSaver:
    """Return a SqliteSaver connected to data/checkpoints.db."""
    return SqliteSaver.from_conn_string("data/checkpoints.db")

def make_thread_config(session_id: str) -> dict:
    """Return a LangGraph thread config for the given session."""
    return {"configurable": {"thread_id": session_id}}
```

### Rules

- Always pass `config=make_thread_config(session_id)` to `graph.invoke()` or `graph.astream()`
- Never reuse the same `thread_id` for unrelated runs — you'll pick up stale checkpoint state
- The checkpointer must be passed to `StateGraph.compile(checkpointer=...)` at graph creation
- `data/checkpoints.db` is runtime-only — never commit it

---

## Graph Creation Pattern

```python
def create_hr_graph() -> CompiledStateGraph:
    builder = StateGraph(HRState)

    builder.add_node("intake", intake_node)
    builder.add_node("policy_expert", policy_expert_node)
    builder.add_node("resume_analyst", resume_analyst_node)
    builder.add_node("decision_maker", decision_maker_node)
    builder.add_node("notify", notify_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "policy_expert")
    builder.add_edge("intake", "resume_analyst")
    builder.add_edge("policy_expert", "decision_maker")
    builder.add_edge("resume_analyst", "decision_maker")
    builder.add_edge("decision_maker", "notify")
    builder.add_edge("notify", END)

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)
```

---

## Common LangGraph Mistakes in This Codebase

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `{**state, ...}` in parallel node | One parallel node's output disappears | Return only owned keys |
| Missing `make_thread_config()` | Checkpoint not saved, runs not resumable | Always pass thread config |
| New field not in HRState | `KeyError` at node access | Add to TypedDict first |
| Edges not wired for new node | Node never executes | Add `add_edge()` calls |
| Graph recompiled without checkpointer | `checkpoint` attribute missing | Pass `checkpointer=get_checkpointer()` to `compile()` |
