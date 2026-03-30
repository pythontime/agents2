# Pre-Commit Checklist — Contoso HR Agent

Run this checklist before ANY commit to `src/contoso_hr/`. Block the commit on any
CRITICAL or HIGH failure.

---

## 1. Automated Checks (Run These Commands)

```bash
# From contoso-hr-agent/
uv run ruff check src/ tests/        # Must report zero issues
uv run pytest tests/ -v              # Must pass with zero failures
```

If either command fails, fix it before continuing.

---

## 2. LangGraph State Integrity

- [ ] **No `{**state, ...}` in parallel nodes** — `policy_expert_node` and
  `resume_analyst_node` return only their owned keys (see ownership map in
  `references/langgraph-patterns.md`)
- [ ] **New HRState fields declared** — Any new state key is added to the
  `HRState` TypedDict in `graph.py`
- [ ] **Fan-in edges intact** — Both `policy_expert → decision_maker` and
  `resume_analyst → decision_maker` edges exist in `graph.py`
- [ ] **`make_thread_config()` used** — All `graph.invoke()` and `graph.astream()`
  calls pass a thread config

---

## 3. CrewAI Coupling

- [ ] **One Crew per node** — No node creates `Crew(agents=[a, b], ...)`
- [ ] **`allow_delegation=False`** on all Agents
- [ ] **LLM set in `Agent.create()`** — Not inside task factories or node functions
- [ ] **`verbose` is correct** — `False` for ChatConcierge, `True` for all pipeline agents
- [ ] **Task descriptions inject state** — Resume text and policy context are
  in the `description` string, not passed as separate context

---

## 4. Pydantic Model Chain

- [ ] **`model_dump()` / `model_validate_json()`** — No `.dict()` or `.parse_raw()` calls
- [ ] **Disposition uses `DISPOSITION` Literal** — No plain `str` for disposition fields
- [ ] **New fields at correct chain stage** — Input fields in `ResumeSubmission`,
  analyst fields in `CandidateEval`, decision fields in `HRDecision`,
  final record in `EvaluationResult`
- [ ] **`Optional[T] = None`** for any new nullable fields

---

## 5. MCP Server

- [ ] **Transport parity** — New tools work in both SSE and stdio (no transport-specific code)
- [ ] **Tool handlers return `str`** — Not dicts, lists, or Pydantic models
- [ ] **No exceptions raised from tool handlers** — Return error strings instead
- [ ] **Sampling only in read-only tools** — `ctx.sample()` not used in state-mutating tools
- [ ] **Elicitation has decline path** — `ctx.elicit()` calls have fallback for user cancellation

---

## 6. Security

- [ ] **No SQL string interpolation** — All SQLite queries use `?` parameterized form
- [ ] **No hardcoded credentials** — No API keys, endpoints, or passwords in source files
- [ ] **No new `data/` files committed** — `data/` is runtime-only
- [ ] **`.env` not committed** — Verify with `git status`

---

## 7. Demo Readiness (For Teaching Demo Commits)

- [ ] Engine starts: `uv run hr-engine` prints 4 URIs with no errors
- [ ] MCP starts: `uv run hr-mcp --stdio` launches without errors
- [ ] At least one sample resume exists or can be uploaded
- [ ] All four disposition CSS classes present in `web/candidates.html`

---

## Commit Gate

| Result | Action |
|--------|--------|
| All checks pass | Commit is safe to proceed |
| Any CRITICAL (LangGraph state, SQL injection, credentials) | Block commit — fix first |
| Any HIGH (CrewAI coupling, Pydantic v2, MCP transport) | Block commit — fix first |
| MEDIUM/LOW only | Proceed but note in commit message |
