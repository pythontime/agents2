---
name: hr-pipeline-reviewer
description: |
  Pipeline review and architectural validation skill for the Contoso HR Agent project.
  Covers LangGraph + CrewAI + FastMCP 2 + Pydantic v2 patterns and the rules specific
  to this codebase. Use when reviewing any change to src/contoso_hr/ or when adding new
  pipeline components.
---

# HR Pipeline Reviewer

Expert review skill for the **Contoso HR Agent** — a LangGraph + CrewAI + FastMCP 2
pipeline for evaluating Microsoft Certified Trainer (MCT) candidates against HR policy.

## When to Activate

| Trigger | Action |
|---------|--------|
| New or modified file in `src/contoso_hr/` | Full review pass |
| New CrewAI agent or LangGraph node | Run `checklists/new-agent.md` |
| New MCP tool, resource, or prompt | Run `checklists/new-mcp-tool.md` |
| Unexpected pipeline disposition | Trace HRState through all nodes |
| Pre-commit | Run `checklists/pre-commit.md` |
| Demo prep | Run demo-readiness checks in agent definition |

## Reference Guides

Load the relevant guide before reviewing — do not rely on memory alone:

| Guide | When to Read |
|-------|-------------|
| [`references/langgraph-patterns.md`](references/langgraph-patterns.md) | graph.py, HRState, node functions, checkpoints |
| [`references/crewai-coupling.md`](references/crewai-coupling.md) | agents.py, tasks.py, tools.py, Crew kickoff |
| [`references/mcp-primitives.md`](references/mcp-primitives.md) | mcp_server/server.py, all five primitives |
| [`references/pydantic-models.md`](references/pydantic-models.md) | models.py, model chain, field validators |

## Checklists

| Checklist | Use For |
|-----------|---------|
| [`checklists/pre-commit.md`](checklists/pre-commit.md) | Any commit to src/contoso_hr/ |
| [`checklists/new-agent.md`](checklists/new-agent.md) | Adding a CrewAI agent or LangGraph node |
| [`checklists/new-mcp-tool.md`](checklists/new-mcp-tool.md) | Adding an MCP primitive |

## Priority Order

Always review in this sequence — stop and fix CRITICAL issues before proceeding:

1. **CRITICAL — Architecture** — LangGraph/CrewAI coupling rules, MCP primitive rules
2. **HIGH — Correctness** — State corruption, data loss, SQL injection, model chain drift
3. **HIGH — Demo Safety** — Anything that would break a live teaching demo
4. **MEDIUM — Integration** — Pydantic drift, tool coupling, transport parity
5. **LOW — Style** — Naming, ruff compliance, docstrings

## The Five Non-Negotiables

These are the five rules most commonly violated in this codebase. Check these first:

1. **Parallel nodes return partial state only** — No `{**state, ...}` in `policy_expert` or `resume_analyst`
2. **One Crew per LangGraph node** — No multi-agent crews inside a single node function
3. **LLM injected at Agent construction** — Never called inside task factory functions
4. **All four dispositions are Literals** — Never use plain `str` for disposition fields
5. **MCP tools work in both transports** — No SSE-only or stdio-only code paths

## Quick Diagnosis: Wrong Disposition

When a candidate gets an unexpected disposition, trace this path:

```
1. Check intake node: was ResumeSubmission parsed correctly?
   → src/contoso_hr/pipeline/graph.py: intake()

2. Check policy_expert output: what policy_context_summary was produced?
   → src/contoso_hr/pipeline/tasks.py: PolicyExpertTask

3. Check resume_analyst output: what skills_match_score was assigned?
   → src/contoso_hr/pipeline/tasks.py: ResumeAnalystTask
   → Did brave_web_search fire? Check tool call logs.

4. Check decision_maker input: did it receive both policy + analyst outputs?
   → Verify LangGraph merged partial state correctly (graph.py fan-in edges)

5. Check disposition thresholds in prompts.py:
   → Strong Match: 80+, Possible Match: 55-79, Needs Review: 35-54, Not Qualified: <35
```

## Key File Map

```
src/contoso_hr/
├── pipeline/
│   ├── graph.py          ← LangGraph StateGraph, HRState, 5 node functions
│   ├── agents.py         ← 4 CrewAI Agent class definitions
│   ├── tasks.py          ← CrewAI Task factories (inject state into descriptions)
│   ├── tools.py          ← @tool query_hr_policy + brave_web_search
│   └── prompts.py        ← System prompts + disposition thresholds
├── models.py             ← Full Pydantic v2 model chain
├── config.py             ← Azure AI Foundry factories
├── mcp_server/
│   └── server.py         ← FastMCP 2, all 5 primitives
├── knowledge/
│   ├── retriever.py      ← ChromaDB query → PolicyContext
│   └── vectorizer.py     ← Doc ingestion → embeddings → ChromaDB
├── memory/
│   ├── sqlite_store.py   ← HRSQLiteStore (candidates + evaluations)
│   └── checkpoints.py    ← SqliteSaver factory
└── engine.py             ← FastAPI endpoints + chat session management
```
