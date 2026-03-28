"""
Token tracking utilities for cost-aware AI agent development.

Provides helpers to extract token usage from LLM responses and calculate costs.
Supports Azure AI Foundry (GPT-4o), OpenAI, and Anthropic pricing.
"""

from __future__ import annotations

from typing import Any, Optional

from ..models import AgentTokens, PipelineTokens, TokenUsage


# Pricing per 1M tokens (as of early 2026)
# NOTE: More specific model names must come BEFORE generic ones.
PRICING: dict[str, dict[str, float]] = {
    # Azure AI Foundry / OpenAI
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Text embeddings (input only, no output tokens)
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    # Anthropic (for reference)
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


def extract_token_usage(response: Any, model_name: str) -> Optional[TokenUsage]:
    """Extract token usage from a LangChain LLM response.

    Args:
        response: LLM response object.
        model_name: Model identifier for cost lookup.

    Returns:
        TokenUsage with stats and cost estimate, or None.
    """
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        response_meta = getattr(response, "response_metadata", {})
        usage = response_meta.get("usage") or response_meta.get("token_usage")

    if not usage:
        return None

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or getattr(usage, "input_tokens", 0)
        or 0
    )
    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or getattr(usage, "output_tokens", 0)
        or 0
    )
    total_tokens = (
        usage.get("total_tokens")
        or getattr(usage, "total_tokens", input_tokens + output_tokens)
    )

    cost = calculate_cost(input_tokens, output_tokens, model_name)

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        model_name=model_name,
        estimated_cost_usd=cost,
    )


def calculate_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Estimate cost in USD based on token counts and model.

    Args:
        input_tokens: Prompt/input token count.
        output_tokens: Completion/output token count.
        model_name: Model identifier (partial match supported).

    Returns:
        Estimated USD cost (6 decimal precision).
    """
    pricing = None
    for key in PRICING:
        if key in model_name.lower():
            pricing = PRICING[key]
            break
    if not pricing:
        pricing = {"input": 3.00, "output": 15.00}  # conservative default

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def aggregate_pipeline_tokens(agent_usages: list[AgentTokens]) -> PipelineTokens:
    """Aggregate token usage from all pipeline agents.

    Args:
        agent_usages: Per-agent token records.

    Returns:
        PipelineTokens with totals, breakdown, and efficiency metrics.
    """
    total_input = sum(a.usage.input_tokens for a in agent_usages)
    total_output = sum(a.usage.output_tokens for a in agent_usages)
    total = sum(a.usage.total_tokens for a in agent_usages)
    total_cost = sum(a.usage.estimated_cost_usd or 0 for a in agent_usages)

    cost_breakdown = {a.agent_name: a.usage.estimated_cost_usd or 0 for a in agent_usages}

    avg_tokens = total / len(agent_usages) if agent_usages else 0
    max_tokens = max((a.usage.total_tokens for a in agent_usages), default=0)
    context_pct = (max_tokens / 128_000) * 100  # GPT-4o context window
    io_ratio = total_input / total_output if total_output > 0 else 0

    efficiency_metrics = {
        "average_tokens_per_agent": round(avg_tokens, 2),
        "max_agent_tokens": max_tokens,
        "estimated_context_window_usage_percent": round(context_pct, 2),
        "input_output_ratio": round(io_ratio, 3),
        "total_agents": len(agent_usages),
        "cost_per_agent_avg": round(total_cost / len(agent_usages), 6) if agent_usages else 0,
    }

    return PipelineTokens(
        agents=agent_usages,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total,
        estimated_total_cost_usd=round(total_cost, 6) if total_cost else None,
        cost_breakdown=cost_breakdown,
        efficiency_metrics=efficiency_metrics,
    )
