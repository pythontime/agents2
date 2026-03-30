# New Agent Checklist — Contoso HR Agent

Use this checklist when adding a new CrewAI agent and/or LangGraph node to the pipeline.
Work through sections in order — each section depends on the previous.

---

## Phase 1 — Define the Agent's Responsibility

Before writing any code, answer these questions:

- [ ] **What pipeline stage does this agent occupy?**
  - Is it a new parallel fan-out branch (like policy_expert / resume_analyst)?
  - Is it a new sequential stage (after decision_maker)?
  - Is it a chat-style agent (like ChatConcierge)?

- [ ] **What state keys does it read?** List them.
- [ ] **What state keys does it write?** List them (these must be unique — no key may be
  written by more than one node).

- [ ] **What tools does it need?** Choose from:
  - `query_hr_policy` — ChromaDB semantic search
  - `brave_web_search` — External web research
  - None (pure reasoning, like DecisionMaker)
  - New tool (requires separate tool implementation — see rules below)

---

## Phase 2 — Update Models

- [ ] **Add new state keys to `HRState` TypedDict** in `graph.py`
- [ ] **Add corresponding fields to the appropriate Pydantic model** in `models.py`:
  - Analyst outputs → `CandidateEval`
  - Policy outputs → `HRDecision` (or new intermediate model if warranted)
  - Final outputs → `EvaluationResult`
- [ ] **New fields are `Optional[T] = None`** (nodes may not always run)
- [ ] **Disposition type unchanged** unless explicitly replacing it — use `DISPOSITION` Literal

---

## Phase 3 — Implement the Agent

In `agents.py`:

```python
class MyNewAgent:
    ROLE = "..."
    GOAL = "..."
    BACKSTORY = "..."   # At least 3 sentences — LLM uses this as system context

    @classmethod
    def create(cls, config: Config) -> Agent:
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=config.get_crew_llm(),   # ← Must be here, not in task factory
            tools=[...],                  # ← Tool instances
            verbose=True,                 # ← True for pipeline agents
            allow_delegation=False,       # ← Always False
            max_iter=3,
        )
```

- [ ] ROLE is a job title, not a description
- [ ] GOAL is a single sentence describing the output expected
- [ ] BACKSTORY includes domain expertise, codebase context, and MCT-specific criteria
- [ ] `allow_delegation=False`
- [ ] `max_iter=3` (adjust only if agent legitimately needs more iterations)
- [ ] `verbose=True` for pipeline agents, `verbose=False` for chat agents

---

## Phase 4 — Implement the Task Factory

In `tasks.py`:

```python
def MyNewAgentTask(
    agent: Agent,
    state_key_1: str,
    state_key_2: Optional[SomeModel] = None,  # Optional for parallel node inputs
) -> Task:
    return Task(
        description=f"""
        [Detailed instructions with state injected as f-string values]

        STATE_KEY_1: {state_key_1}
        STATE_KEY_2: {state_key_2.summary if state_key_2 else 'Not yet available.'}
        """,
        expected_output=(
            "Structured output with fields: field_a (str), field_b (float 0-100), ..."
        ),
        agent=agent,
    )
```

- [ ] All relevant state injected into `description` string
- [ ] `expected_output` lists exact field names the LLM should produce
- [ ] Optional state handled gracefully (fallback text, not None check errors)
- [ ] No LLM calls, config lookups, or async operations inside the factory

---

## Phase 5 — Implement the LangGraph Node

In `graph.py`:

```python
def my_new_agent_node(state: HRState) -> dict:
    """One-line docstring describing what this node does."""
    config = get_config()
    agent = MyNewAgent.create(config)
    task = MyNewAgentTask(
        agent=agent,
        state_key_1=state["state_key_1"],
        state_key_2=state.get("state_key_2"),   # .get() for Optional fields
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()

    # Parse result.raw → structured fields
    # ...

    return {
        "new_key_1": parsed_value_1,    # ← ONLY keys this node owns
        "new_key_2": parsed_value_2,
        # Never return {**state, ...}
    }
```

- [ ] One `Crew` instance with one agent and one task
- [ ] `result.raw` accessed for string output (not `str(result)`)
- [ ] Returns ONLY owned state keys (no `{**state, ...}`)
- [ ] Uses `state.get()` for Optional fields (not `state["key"]` which raises KeyError)

---

## Phase 6 — Wire the Graph

In `graph.py`, `create_hr_graph()`:

- [ ] `builder.add_node("my_new_agent", my_new_agent_node)` added
- [ ] Upstream edge added: `builder.add_edge("upstream_node", "my_new_agent")`
- [ ] Downstream edge added: `builder.add_edge("my_new_agent", "downstream_node")`
- [ ] If parallel: both fan-out edges from `intake` and fan-in edges to `decision_maker`
  are correct

**Verify the full topology** by listing all `add_edge()` calls in order and confirming
the DAG matches the intended pipeline diagram.

---

## Phase 7 — Implement New Tools (If Required)

If the new agent needs a tool that doesn't exist yet:

In `tools.py`:

```python
@tool("my_new_tool")
def my_new_tool(query: str) -> str:
    """One-sentence description (shown to LLM as tool manifest entry).

    Args:
        query: Description of this parameter.

    Returns:
        Description of what the tool returns as a string.
    """
    # No side effects on HRState
    # Return str — serialize any structured data
    result = external_call(query)
    return str(result)
```

- [ ] Docstring is written for LLM consumption (clear, concise, accurate)
- [ ] Returns `str`
- [ ] No HRState mutation
- [ ] Handles errors with a return string, not a raised exception

---

## Phase 8 — Tests

- [ ] Unit test for the new agent's `create()` method (mock `Config`)
- [ ] Unit test for the new task factory (verify state injection)
- [ ] Integration test for the new node function (mock `Crew.kickoff()`)
- [ ] Verify new node does not break existing `tests/` suite: `uv run pytest tests/ -v`

---

## Phase 9 — Final Review

Run the full pre-commit checklist: `checklists/pre-commit.md`
