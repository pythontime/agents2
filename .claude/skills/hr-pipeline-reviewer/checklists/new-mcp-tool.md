# New MCP Primitive Checklist — Contoso HR Agent

Use this checklist when adding any MCP primitive (tool, resource, prompt, sampling,
elicitation) to `src/contoso_hr/mcp_server/server.py`.

---

## All Primitives — Common Rules

Before writing any primitive, confirm:

- [ ] **Which primitive type?** Tool / Static Resource / Resource Template / Prompt /
  Sampling / Elicitation
- [ ] **Read-only or state-mutating?** State-mutating primitives require extra review
- [ ] **Transport tested?** Must work in both SSE (`:8081/sse`) and stdio

---

## Adding a Tool

```python
@mcp.tool()
async def my_tool(param: str) -> str:
    """One-sentence description. Used as the MCP tool manifest entry.

    Args:
        param: Description of this parameter.

    Returns:
        Description of the string output.
    """
    # Implementation
    return result_str
```

- [ ] **Async** — All tool handlers must be `async def`
- [ ] **Returns `str`** — Use `model_dump_json()` for Pydantic, `json.dumps()` for dicts
- [ ] **Docstring describes the tool for LLM** — Not just for developers
- [ ] **Error path returns string** — `return f"Error: {e}"` not `raise e`
- [ ] **Read-only tools don't call `ctx.sample()`** — Sampling is for summary generation only
- [ ] **State-mutating tools verified** — Confirm the tool needs to write; if unsure, make it read-only
- [ ] **No transport-specific code** — Works identically in SSE and stdio

---

## Adding a Static Resource

```python
@mcp.resource("myscheme://myname")
async def my_resource() -> str:
    """Description of what this resource returns."""
    return json.dumps(data, indent=2)
```

- [ ] **URI format: `scheme://name`** — No `{}` placeholders in a static resource URI
- [ ] **Async** — `async def`
- [ ] **Returns `str`** — Serialize structured data to JSON string
- [ ] **Idempotent** — Same URI always returns same shape of data (values may change)
- [ ] **Docstring** present

---

## Adding a Resource Template

```python
@mcp.resource("myscheme://{param_name}")
async def my_template(param_name: str) -> str:
    """Description of what this template returns for a given param_name."""
    # param_name is bound from URI at runtime
    result = lookup(param_name)
    if result is None:
        return f"# Not Found\n\n`{param_name}` does not exist."
    return format_result(result)
```

- [ ] **URI uses `{param}` placeholder** — Matches the function parameter name exactly
- [ ] **Not-found path returns a string** — Not `None`, not an exception
- [ ] **Parameter name matches** — URI `{param}` and function `param: str` must be identical
- [ ] **Async + returns `str`**

---

## Adding a Prompt

```python
@mcp.prompt()
async def my_prompt(required_param: str, optional_param: str = "default") -> list[dict]:
    """Short description of when to use this prompt."""
    return [
        {"role": "system", "content": SOME_SYSTEM_PROMPT},
        {"role": "user", "content": f"Do something with: {required_param}"},
    ]
```

- [ ] **Returns `list[dict]`** — Each dict has `"role"` and `"content"` keys
- [ ] **Optional params have defaults** — So MCP Inspector can render without all fields
- [ ] **Imports system prompts from `pipeline/prompts.py`** — Don't duplicate prompt text
- [ ] **Async** — `async def`

---

## Adding Sampling (`ctx.sample()`)

Only add sampling to read-only tools that generate narrative content.

```python
@mcp.tool()
async def my_summary_tool(entity_id: str, ctx: Context) -> str:
    """Generate a narrative summary using the connected LLM."""
    data = fetch_data(entity_id)
    if data is None:
        return f"Entity {entity_id!r} not found."

    prompt = f"Summarize this data in 2-3 sentences:\n\n{data}"
    result = await ctx.sample(prompt)
    return result.text   # ← .text not .content
```

- [ ] **`ctx: Context` parameter** — Must be in signature to receive context
- [ ] **`await ctx.sample(prompt_str)`** — Returns `SamplingMessage`
- [ ] **`.text` accessor** — Not `.content` or `str(result)`
- [ ] **Tool is read-only** — Never mutate state before or after `ctx.sample()`
- [ ] **Graceful fallback** — Handle `NotImplementedError` if client doesn't support sampling:
  ```python
  try:
      result = await ctx.sample(prompt)
      return result.text
  except NotImplementedError:
      return f"Summary unavailable (client does not support sampling). Raw data:\n{data}"
  ```

---

## Adding Elicitation (`ctx.elicit()`)

Only add elicitation to tools that trigger expensive or irreversible operations.

```python
@mcp.tool()
async def my_confirmed_action(param: str, ctx: Context) -> str:
    """Perform action after user confirmation."""
    confirmation = await ctx.elicit(
        message="Confirm you want to proceed with this action?",
        schema={
            "type": "object",
            "properties": {
                "confirmed": {
                    "type": "boolean",
                    "title": "Confirm",
                    "description": "Check to proceed.",
                }
            },
            "required": ["confirmed"],
        },
    )

    # ← ALWAYS handle decline
    if not confirmation.data.get("confirmed"):
        return "Action cancelled by user."

    # Proceed with action
    result = do_action(param)
    return str(result)
```

- [ ] **`ctx: Context` parameter** in signature
- [ ] **Decline path handled** — Check `confirmed` before proceeding; return cancellation message
- [ ] **No long-running setup before `ctx.elicit()`** — Keep pre-elicit code minimal
- [ ] **JSON Schema is valid** — Test schema with a JSON Schema validator
- [ ] **`confirmation.data.get("confirmed")`** — Use `.get()` not `["confirmed"]`

---

## After Adding Any Primitive

- [ ] **Manual test in MCP Inspector** (stdio transport):
  ```bash
  uv run hr-mcp --stdio
  # In separate terminal:
  npx @modelcontextprotocol/inspector uv run hr-mcp --stdio
  ```
- [ ] **Manual test via SSE** — Start `uv run hr-mcp`, verify tool appears in Inspector
- [ ] **`uv run ruff check src/`** — Zero issues
- [ ] **`uv run pytest tests/`** — All pass
- [ ] **Update `CLAUDE.md`** if the new primitive changes the MCP server's capability list

---

## MCP Primitive Count (Keep This Updated)

Current primitive inventory in `mcp_server/server.py`:

| Type | Name | Read/Write |
|------|------|------------|
| Tool | `get_candidate` | Read |
| Tool | `list_candidates` | Read |
| Tool | `trigger_resume_evaluation` | Write |
| Tool | `query_policy` | Read |
| Tool | `generate_eval_summary` (sampling) | Read |
| Tool | `confirm_and_evaluate` (elicitation) | Write |
| Static Resource | `schema://candidate` | Read |
| Static Resource | `stats://evaluations` | Read |
| Static Resource | `samples://resumes` | Read |
| Static Resource | `config://settings` | Read |
| Resource Template | `candidate://{candidate_id}` | Read |
| Resource Template | `policy://{topic}` | Read |
| Prompt | `evaluate_resume` | — |
| Prompt | `policy_query` | — |
| Prompt | `disposition_review` | — |

Update this table when adding or removing primitives.
