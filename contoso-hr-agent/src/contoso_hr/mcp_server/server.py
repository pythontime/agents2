"""
Contoso HR Agent — FastMCP 2 MCP Server.

Exposes resume/candidate tools, resources, and prompts via SSE transport.
Port 8081 (killed on startup).

Transport: SSE (Server-Sent Events) — connect with MCP Inspector at:
  http://localhost:5173 → SSE URL: http://localhost:8081/sse

Tools:
  get_candidate(candidate_id)          — full evaluation result
  list_candidates(limit, decision)     — recent evaluations
  trigger_resume_evaluation(text, fn)  — run pipeline directly
  query_policy(question)               — ChromaDB knowledge retrieval

Resources:
  schema://candidate                   — CandidateEval JSON schema
  stats://evaluations                  — aggregate stats

Prompts:
  evaluate_resume(resume_text, role)   — evaluation prompt template
  policy_query(question)               — policy Q&A prompt template
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# FastMCP 2 Server Instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="contoso-hr-agent",
    instructions=(
        "The Contoso HR Agent MCP server provides tools for querying candidate evaluations, "
        "triggering resume screening, and searching the HR policy knowledge base. "
        "All evaluations are performed by a 3-agent AI pipeline (PolicyExpert, ResumeAnalyst, "
        "DecisionMaker) running on Azure AI Foundry."
    ),
)


def _get_store():
    from contoso_hr.config import get_config
    from contoso_hr.memory.sqlite_store import HRSQLiteStore
    config = get_config()
    return HRSQLiteStore(config.data_dir / "hr.db")


def _get_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_candidate(candidate_id: str) -> dict:
    """Get the full AI evaluation result for a specific candidate.

    Args:
        candidate_id: Unique candidate identifier (8-char hex string).

    Returns:
        Complete EvaluationResult including scores, decision, reasoning, and next steps.
    """
    store = _get_store()
    result = store.get_result(candidate_id)
    if result is None:
        return {"error": f"Candidate '{candidate_id}' not found"}
    return result.model_dump()


@mcp.tool()
async def list_candidates(
    limit: int = 20,
    decision_filter: str = "",
) -> list[dict]:
    """List recent candidate evaluations.

    Args:
        limit: Maximum number of results to return (default 20).
        decision_filter: Filter by disposition: 'Strong Match', 'Possible Match',
            'Needs Review', 'Not Qualified', or '' for all.

    Returns:
        List of candidate summaries with name, decision, scores, and timestamp.
    """
    store = _get_store()
    if decision_filter:
        results = store.get_candidates_by_decision(decision_filter, limit)
    else:
        results = store.get_recent_candidates(limit)
    return [c.model_dump() for c in results]


@mcp.tool()
async def trigger_resume_evaluation(
    resume_text: str,
    filename: str = "mcp_submission.txt",
) -> dict:
    """Submit resume text directly for AI evaluation (bypasses file watcher).

    Runs the full LangGraph + CrewAI pipeline synchronously and returns results.

    Args:
        resume_text: Plain text content of the resume.
        filename: Display name for the submission (e.g. 'candidate_jane.txt').

    Returns:
        EvaluationResult dict with decision, scores, and next steps.
        Processing may take 30-120 seconds depending on LLM response times.
    """
    from contoso_hr.watcher.process_resume import process_resume_text

    result = process_resume_text(resume_text, filename)
    if result is None:
        return {"error": "Evaluation failed — check server logs for details"}
    return result.model_dump()


@mcp.tool()
async def query_policy(question: str) -> str:
    """Query the Contoso HR policy knowledge base using semantic search.

    Args:
        question: Natural language question about Contoso HR policy.
                  Example: 'What is the compensation band for Level 3?'

    Returns:
        Relevant policy text chunks from ChromaDB.
    """
    from contoso_hr.knowledge.retriever import query_policy_knowledge

    context = query_policy_knowledge(question, k=4)
    if not context.chunks:
        return "No relevant policy content found. Ensure knowledge base has been seeded (uv run hr-seed)."

    parts = []
    for chunk, source in zip(context.chunks, context.sources):
        parts.append(f"[{source}]\n{chunk}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("schema://candidate")
def candidate_schema() -> str:
    """JSON schema for candidate evaluation results."""
    from contoso_hr.models import EvaluationResult
    return json.dumps(EvaluationResult.model_json_schema(), indent=2)


@mcp.resource("stats://evaluations")
def evaluation_stats() -> str:
    """Current aggregate statistics for all candidate evaluations."""
    store = _get_store()
    return json.dumps(store.get_stats(), indent=2)


@mcp.resource("samples://resumes")
def list_sample_resumes() -> str:
    """List of available sample resume files for testing."""
    root = _get_project_root()
    sample_dir = root / "sample_resumes"
    if not sample_dir.exists():
        return json.dumps({"samples": []})
    files = sorted(sample_dir.glob("*.txt")) + sorted(sample_dir.glob("*.md"))
    return json.dumps({
        "samples": [
            {"filename": f.name, "size_bytes": f.stat().st_size}
            for f in files
        ]
    }, indent=2)


@mcp.resource("config://settings")
def get_config_settings() -> str:
    """Current application configuration (no secrets)."""
    from contoso_hr.config import get_config
    config = get_config()
    return json.dumps({
        "chat_model": config.azure_foundry_chat_model,
        "embedding_model": config.azure_foundry_embedding_model,
        "api_version": config.azure_foundry_api_version,
        "endpoint": config.azure_foundry_endpoint,
        "azure_tenant_id": config.azure_tenant_id,
        "azure_subscription_id": config.azure_subscription_id,
        "azure_resource_group": config.azure_resource_group,
        "watch_poll_seconds": config.watch_poll_seconds,
        "log_level": config.log_level,
        "engine_port": config.engine_port,
        "mcp_port": config.mcp_port,
        "incoming_dir": str(config.incoming_dir),
        "outgoing_dir": str(config.outgoing_dir),
    }, indent=2)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def evaluate_resume(resume_text: str, role: str = "") -> str:
    """Generate a structured trainer resume evaluation prompt.

    Args:
        resume_text: The resume content to evaluate.
        role: Optional target role (e.g. 'Senior Trainer — Azure Infrastructure').
    """
    role_context = f" for the role of {role}" if role else " for a Contoso technical trainer role"
    return (
        f"Please evaluate this trainer candidate resume{role_context}.\n\n"
        f"Contoso hires technical trainers for Microsoft Azure, M365, and Security "
        f"certification courses. Assess:\n"
        f"- MCT (Microsoft Certified Trainer) status\n"
        f"- Relevant Microsoft certifications (AZ-104, AZ-305, SC-300, AI-102, etc.)\n"
        f"- Training delivery volume and learner satisfaction scores\n"
        f"- Curriculum development or course authorship experience\n"
        f"- Hands-on technical depth\n\n"
        f"Provide scores (0-100) for skills match and experience, list key strengths "
        f"and red flags, and recommend one of: Strong Match, Possible Match, "
        f"Needs Review, Not Qualified.\n\n"
        f"RESUME:\n{resume_text}"
    )


@mcp.prompt()
def policy_query(question: str) -> str:
    """Generate a structured HR policy query prompt.

    Args:
        question: The HR policy question to answer.
    """
    return (
        f"Using Contoso HR policy documentation, please answer the following question "
        f"accurately and concisely. Cite the relevant policy section if applicable.\n\n"
        f"Question: {question}"
    )
