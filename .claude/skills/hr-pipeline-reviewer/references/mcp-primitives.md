# FastMCP 2 Primitives — Contoso HR Agent

Reference for `src/contoso_hr/mcp_server/server.py`.

This project implements **all five MCP primitives** as a teaching example. Each section
covers the pattern used and the rules to follow when adding or modifying primitives.

---

## Transport Setup

```python
# mcp_server/__main__.py
import argparse
from contoso_hr.mcp_server.server import mcp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()

    if args.stdio:
        mcp.run(transport="stdio")           # MCP Inspector
    else:
        mcp.run(transport="sse", port=8081)  # SSE for web clients
```

### Transport Parity Rule

Every tool handler must work identically in both transports. Never write:

```python
# ❌ WRONG — SSE-only pattern
@mcp.tool()
async def my_tool(ctx: Context) -> str:
    if hasattr(ctx, "sse_connection"):  # This doesn't exist in stdio
        ...
```

Both transports expose the same `Context` API. Use only documented `ctx.*` methods.

---

## Primitive 1 — Tools

Standard request/response functions. Six tools in this project.

```python
@mcp.tool()
async def get_candidate(candidate_id: str) -> str:
    """Retrieve a single candidate's full evaluation result as JSON.

    Args:
        candidate_id: The candidate's unique identifier (UUID string).

    Returns:
        JSON string of the EvaluationResult for this candidate, or an
        error message if the candidate is not found.
    """
    store = HRSQLiteStore()
    result = store.get_evaluation(candidate_id)
    if result is None:
        return f"Candidate {candidate_id!r} not found."
    return result.model_dump_json(indent=2)
```

### Tool Rules

1. **Return `str`** — MCP tools must return strings. Use `model_dump_json()` for Pydantic
   models, `json.dumps()` for dicts.

2. **Descriptive docstring** — The docstring is the tool's MCP description. Write it
   for an LLM reading it as a tool manifest.

3. **No state mutation in read tools** — `get_candidate`, `list_candidates`, `query_policy`
   are read-only. Only `trigger_resume_evaluation` and `confirm_and_evaluate` modify state.

4. **Error strings, not exceptions** — Return a descriptive error string instead of raising
   from tool handlers. MCP clients receive the exception message anyway, but a clean string
   is better for teaching demos.

---

## Primitive 2 — Resources (Static)

Static resources are fixed URIs that return a consistent payload.

```python
@mcp.resource("schema://candidate")
async def candidate_schema() -> str:
    """JSON Schema for the EvaluationResult model."""
    return json.dumps(EvaluationResult.model_json_schema(), indent=2)

@mcp.resource("stats://evaluations")
async def evaluation_stats() -> str:
    """Aggregate statistics across all evaluated candidates."""
    store = HRSQLiteStore()
    stats = store.get_stats()
    return json.dumps(stats, indent=2)
```

### Primitive 3 — Resources (Templates)

Parameterized resources use `{param}` placeholders in the URI:

```python
@mcp.resource("candidate://{candidate_id}")
async def candidate_resource(candidate_id: str) -> str:
    """Formatted markdown profile for a candidate.

    Returns a human-readable summary suitable for a hiring committee review.
    """
    store = HRSQLiteStore()
    result = store.get_evaluation(candidate_id)
    if result is None:
        return f"# Candidate Not Found\n\n`{candidate_id}` does not exist."
    return _format_candidate_markdown(result)

@mcp.resource("policy://{topic}")
async def policy_resource(topic: str) -> str:
    """Semantic search over HR policy knowledge base for a topic.

    Args:
        topic: The policy topic to search (e.g., 'MCT certification requirements').
    """
    config = get_config()
    result = query_policy_knowledge(topic, k=5)
    return "\n\n---\n\n".join(result.chunks)
```

### Resource URI Rules

| URI Format | Use For |
|------------|---------|
| `scheme://name` | Static resources (no parameters) |
| `scheme://{param}` | Parameterized templates |
| `scheme://{param}/subpath` | Nested parameterized templates |

Never mix static and template syntax on the same URI pattern.

---

## Primitive 4 — Sampling (`ctx.sample()`)

Sampling lets the MCP server ask the **connected LLM** to generate content, rather than
calling Azure AI Foundry directly. Used in `generate_eval_summary`.

```python
@mcp.tool()
async def generate_eval_summary(candidate_id: str, ctx: Context) -> str:
    """Generate an executive summary for a candidate evaluation.

    Uses the connected LLM (via MCP sampling) to write a concise briefing
    suitable for a hiring committee. Requires an MCP client that supports sampling.

    Args:
        candidate_id: The candidate's unique identifier.

    Returns:
        A 2-3 paragraph executive summary of the candidate's evaluation.
    """
    store = HRSQLiteStore()
    result = store.get_evaluation(candidate_id)
    if result is None:
        return f"Candidate {candidate_id!r} not found."

    # Build sampling request — the connected LLM generates the summary
    prompt = (
        f"Write a 2-3 paragraph executive hiring committee briefing for:\n\n"
        f"{result.model_dump_json(indent=2)}\n\n"
        f"Focus on disposition rationale, key strengths, and recommended next steps."
    )
    summary = await ctx.sample(prompt)
    return summary.text
```

### Sampling Rules

1. **Read-only use only** — `ctx.sample()` is for generating narrative content from
   existing data. Never use it to make hiring decisions or write to the database.

2. **Requires sampling-capable client** — Not all MCP clients support sampling. The tool
   should degrade gracefully if `ctx.sample()` raises `NotImplementedError`.

3. **Inject structured data** — Pass the full Pydantic model JSON into the prompt so
   the LLM has precise, validated data rather than natural language summaries.

4. **`summary.text`** — `ctx.sample()` returns a `SamplingMessage`. Access the string
   content via `.text`, not `.content` or `str(summary)`.

---

## Primitive 5 — Elicitation (`ctx.elicit()`)

Elicitation pauses a tool and presents a form to the user, resuming only on acceptance.
Used in `confirm_and_evaluate`.

```python
@mcp.tool()
async def confirm_and_evaluate(resume_text: str, session_id: str, ctx: Context) -> str:
    """Trigger a pipeline evaluation after user confirmation.

    Pauses to present a confirmation dialog before running the full
    LangGraph evaluation pipeline. Requires an MCP client that supports elicitation.

    Args:
        resume_text: The full text of the candidate's resume.
        session_id: Unique session identifier for checkpoint tracking.

    Returns:
        The EvaluationResult JSON if confirmed, or a cancellation message.
    """
    # Present confirmation form to user
    confirmation = await ctx.elicit(
        message=f"Run full pipeline evaluation for this resume? ({len(resume_text)} chars)",
        schema={
            "type": "object",
            "properties": {
                "confirmed": {
                    "type": "boolean",
                    "title": "Confirm evaluation",
                    "description": "Check to proceed with the pipeline run.",
                },
                "priority": {
                    "type": "string",
                    "title": "Priority",
                    "enum": ["normal", "urgent"],
                    "default": "normal",
                },
            },
            "required": ["confirmed"],
        },
    )

    # ALWAYS handle the decline path
    if not confirmation.data.get("confirmed"):
        return "Evaluation cancelled by user."

    # Proceed with pipeline run
    graph = create_hr_graph()
    config = make_thread_config(session_id)
    result = graph.invoke(
        {"resume_text": resume_text, "session_id": session_id},
        config=config,
    )
    return result["result"].model_dump_json(indent=2) if result.get("result") else "Pipeline error."
```

### Elicitation Rules

1. **Always handle decline** — `confirmation.data.get("confirmed")` may be `False` or
   absent. Never assume the user accepts. Return a clean cancellation message.

2. **JSON Schema for form** — The `schema` parameter must be valid JSON Schema describing
   the form fields. Use `boolean` for yes/no confirmations.

3. **Elicitation is blocking** — `await ctx.elicit()` suspends the tool until the user
   responds. Do not put long-running setup code before the elicit call.

4. **`confirmation.data`** — `ctx.elicit()` returns an `ElicitationResult`. The user's
   form values are in `.data` as a dict.

---

## Prompts (MCP Prompt Primitive)

MCP prompts are reusable message templates exposed to clients:

```python
@mcp.prompt()
async def evaluate_resume(resume_text: str, role_level: str = "MCT") -> list[dict]:
    """Multi-message prompt for structured resume evaluation training."""
    return [
        {
            "role": "system",
            "content": POLICY_EXPERT_PROMPT,   # from prompts.py
        },
        {
            "role": "user",
            "content": f"Evaluate this {role_level} candidate:\n\n{resume_text}",
        },
    ]
```

### Prompt Rules

1. **Return `list[dict]`** — Each dict has `"role"` and `"content"` keys.
2. **Reuse `prompts.py` constants** — Import system prompts from `pipeline/prompts.py`
   to keep prompts consistent between pipeline agents and MCP prompt templates.
3. **Optional parameters have defaults** — Always provide defaults for optional prompt
   parameters so MCP Inspector can render them without all fields filled in.

---

## Common MCP Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Raising exception in tool handler | Client gets raw Python traceback | Return error string |
| `result.content` instead of `.text` | `AttributeError` on sampling result | Use `.text` |
| Missing decline path in elicitation | `None` or `KeyError` on cancel | Check `confirmed` before proceeding |
| Static URI with `{}` in it | Treated as template, param never bound | Use `scheme://name` for static |
| `ctx.sample()` inside state-mutating tool | Non-deterministic reads | Keep sampling in read-only tools only |
| Transport-specific code | Breaks stdio or SSE | Use only documented `ctx.*` API |
