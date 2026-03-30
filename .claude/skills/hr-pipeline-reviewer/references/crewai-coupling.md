# CrewAI Coupling Patterns — Contoso HR Agent

Reference for `src/contoso_hr/pipeline/agents.py`, `tasks.py`, `tools.py`.

---

## The Four Agents

| Agent | Persona | Tools | Verbose | Used In |
|-------|---------|-------|---------|---------|
| `ChatConciergeAgent` ("Alex") | Friendly HR policy Q&A | `[query_hr_policy]` | `False` | `/api/chat` endpoint |
| `PolicyExpertAgent` | HR policy compliance analyst | `[query_hr_policy]` | `True` | `policy_expert` LangGraph node |
| `ResumeAnalystAgent` | MCT candidate skills evaluator | `[brave_web_search]` | `True` | `resume_analyst` LangGraph node |
| `DecisionMakerAgent` | Senior hiring committee | None (pure reasoning) | `True` | `decision_maker` LangGraph node |

---

## Agent Class Pattern

Each agent is defined as a class with a `create()` classmethod:

```python
class PolicyExpertAgent:
    ROLE = "HR Policy Compliance Analyst"
    GOAL = "Assess candidates against Contoso HR policy and MCT certification requirements"
    BACKSTORY = (
        "You are a meticulous HR policy expert with deep knowledge of Microsoft Certified "
        "Trainer requirements, compensation bands, and Contoso's evaluation rubric. ..."
    )

    @classmethod
    def create(cls, config: Config) -> Agent:
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=config.get_crew_llm(),      # ← LLM injected here, NOT in task
            tools=[query_hr_policy],         # ← tool instances, not strings
            verbose=True,                    # ← True for all pipeline agents
            allow_delegation=False,          # ← ALWAYS False (one agent per crew)
            max_iter=3,                      # ← Prevent runaway tool loops
        )
```

### Rules

1. **LLM injected at construction** — `config.get_crew_llm()` is called inside `create()`,
   not inside task factories or node functions.

2. **`allow_delegation=False`** — Always. We use single-agent crews; delegation would
   silently create a second agent and break the one-crew-per-node guarantee.

3. **`max_iter=3`** — Prevents runaway tool calls during demos. Increase only if a specific
   agent legitimately needs more iterations (e.g., multi-step web research).

4. **Verbose discipline** — ChatConciergeAgent is `verbose=False` (chat stays clean in
   the browser). All pipeline agents are `verbose=True` (Rich output in server logs).

---

## Task Factory Pattern

Task factories in `tasks.py` build `Task` objects with state injected into descriptions:

```python
def PolicyExpertTask(
    agent: Agent,
    resume_text: str,
    policy_context: Optional[PolicyContext] = None,
) -> Task:
    policy_docs = (
        "\n\n".join(policy_context.chunks) if policy_context
        else "Use the query_hr_policy tool to retrieve relevant policy sections."
    )
    return Task(
        description=f"""
        Evaluate the following candidate resume against Contoso HR policy.

        RESUME:
        {resume_text}

        POLICY REFERENCE:
        {policy_docs}

        Assess: MCT eligibility, compliance gaps, recommended certification level,
        and compensation band alignment.
        """,
        expected_output=(
            "A structured assessment with: policy_context_summary (str), "
            "compliance_notes (str), recommended_level (str), compensation_band (str)."
        ),
        agent=agent,
    )
```

### Rules

1. **Inject state into description** — Each task must include all relevant state in the
   task `description` string. CrewAI does not automatically share context between nodes.

2. **Structured `expected_output`** — Always specify the exact field names the task should
   produce. This guides the LLM output format.

3. **No LLM calls in factory** — Task factories are pure constructors. Never call async
   functions, config lookups, or LLM methods inside a task factory.

4. **Optional policy_context** — `ResumeAnalystTask` and `PolicyExpertTask` both accept
   `Optional[PolicyContext]` because they may run before ChromaDB retrieval completes
   in the parallel fan-out.

---

## Crew Node Pattern

Every LangGraph node that uses CrewAI follows this exact pattern:

```python
def policy_expert_node(state: HRState) -> dict:
    """Run the PolicyExpert crew to assess HR policy compliance."""
    config = get_config()
    agent = PolicyExpertAgent.create(config)
    task = PolicyExpertTask(
        agent=agent,
        resume_text=state["resume_text"],
        policy_context=state.get("policy_context"),
    )
    crew = Crew(
        agents=[agent],                      # ← exactly one agent
        tasks=[task],                        # ← exactly one task
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()

    # Parse result string → structured fields
    # (parse with JSON or string extraction as appropriate)
    return {
        "policy_context_summary": extract_field(result, "policy_context_summary"),
        "compliance_notes": extract_field(result, "compliance_notes"),
        # ... only keys this node owns
    }
```

### Rules

1. **One `Crew` per node** — `Crew(agents=[one_agent], tasks=[one_task])`. Never
   `agents=[agentA, agentB]` inside a single node.

2. **`Process.sequential`** — Always. There is only one agent anyway, but be explicit.

3. **Return partial state** — Node returns only the keys from the ownership map.
   See `references/langgraph-patterns.md`.

4. **Parse `result.raw`** — `crew.kickoff()` returns a `CrewOutput` object.
   The string content is in `result.raw`. Parse it to extract structured fields.

---

## Tools

Tools are `@tool`-decorated functions imported directly into agent `tools=[]` lists:

```python
# tools.py
from crewai.tools import tool

@tool("query_hr_policy")
def query_hr_policy(question: str) -> str:
    """Search Contoso HR policy knowledge base for relevant policy sections.

    Args:
        question: The policy question or search query.

    Returns:
        Relevant policy text chunks concatenated as a string.
    """
    config = get_config()
    retriever = PolicyRetriever(config)
    result = retriever.query(question, k=4)
    return "\n\n".join(result.chunks)
```

### Rules

1. **No side effects** — Tools must be stateless. Never write to SQLite or mutate
   HRState from inside a tool.

2. **Return strings** — CrewAI tools must return `str`. Serialize any structured data
   before returning.

3. **Descriptive docstrings** — The docstring IS the tool's description shown to the LLM.
   Write it as if explaining the tool to a non-technical hiring manager.

4. **`max_iter` protection** — Tools that call external APIs (Brave, ChromaDB) are wrapped
   by the `max_iter=3` limit on agents. If a tool is expensive, add a timeout.

---

## LLM Configuration

```python
# config.py — CrewAI uses LiteLLM bridge
def get_crew_llm(self) -> LLM:
    return LLM(
        model=f"azure/{self.chat_model}",   # e.g. "azure/gpt-4o-mini"
        api_base=self.endpoint,
        api_key=self.key,
        api_version="2024-08-01-preview",
    )

# LangChain uses AzureChatOpenAI directly
def get_llm(self) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=self.endpoint,
        azure_deployment=self.chat_model,
        api_key=self.key,
        api_version="2024-08-01-preview",
    )
```

The two LLM factories serve different consumers:
- `get_crew_llm()` → CrewAI `Agent(llm=...)`
- `get_llm()` → Any direct LangChain call (not currently used in pipeline nodes)

Never pass `get_llm()` to a CrewAI Agent — LiteLLM won't recognize it.

---

## Common CrewAI Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `allow_delegation=True` | Silent second agent spawned | Always set `False` |
| LLM in task factory | Config loaded at task build time, not agent start | Move to `Agent.create()` |
| `{**state}` in node return | Clobbers parallel node output | Return only owned keys |
| Plain `str` for disposition | Breaks Pydantic Literal validation | Use the Literal type |
| `result` not `.raw` | `CrewOutput` object treated as string | Access `result.raw` |
| `verbose=True` on ChatConcierge | Chat endpoint logs flood stdout | Always `False` for chat |
