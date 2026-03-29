# Token Tracking and Cost Awareness

**Last Updated:** 2026-03-29

> **Historical reference.** This document described the token tracking and cost estimation
> system built for `oreilly-agent-mvp/` (PM/Dev/QA issue-triage pipeline). That system
> tracked per-agent token usage, calculated USD costs from a pricing table, and displayed
> console summaries after each pipeline run.
>
> The active project (`contoso-hr-agent/`) does not include this token tracking module.
> CrewAI and LangGraph handle LLM calls internally; cost monitoring for Azure AI Foundry
> deployments is done through the Azure portal's built-in metrics and billing dashboards.

## Teaching Relevance

The concepts from the original token tracking implementation remain valuable for the
O'Reilly course:

1. **Cost awareness** -- understand that every LLM call has a measurable cost.
2. **Context window management** -- prompt length directly affects token consumption.
3. **Output length control** -- output tokens are typically more expensive than input.
4. **Multi-agent economics** -- each agent in a pipeline adds to total cost.
5. **Production monitoring** -- Azure AI Foundry provides per-deployment token and cost metrics.

## Where Cost Data Lives Now

For the Contoso HR Agent, monitor LLM costs via:

- **Azure Portal** -- Azure AI Foundry resource metrics (tokens, requests, latency).
- **CrewAI verbose output** -- set `verbose=True` on Crew objects to see per-call details in the console.
- **LangGraph checkpoints** -- `data/checkpoints.db` records state at each node transition.

## Legacy Code Reference

The original implementation lives in `oreilly-agent-mvp/src/agent_mvp/util/token_tracking.py`
and includes:

- `extract_token_usage()` -- extract tokens from LangChain response metadata.
- `calculate_cost()` -- USD cost from token counts and a pricing table.
- `aggregate_pipeline_tokens()` -- sum usage across all agents.
- `format_token_summary()` -- Rich console output.
- `PRICING` dict -- per-model pricing for Claude and GPT families.

See `oreilly-agent-mvp/` for the full source. Do not modify that project unless
explicitly requested.
