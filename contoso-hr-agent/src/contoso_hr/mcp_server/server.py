"""
Contoso HR Agent — FastMCP 2 MCP Server.

Demonstrates all five MCP primitives with domain-relevant examples.

Transport: stdio (MCP Inspector) or SSE on port 8081.
  stdio:  npx @modelcontextprotocol/inspector uv run hr-mcp --stdio
  SSE:    uv run hr-mcp  →  http://localhost:8081/sse

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRIMITIVE 1 — TOOLS  (server-side functions the LLM can call)
  get_candidate(candidate_id)          — full EvaluationResult for one candidate
  list_candidates(limit, decision)     — recent evaluations, optional filter
  trigger_resume_evaluation(text, fn)  — run full LangGraph + CrewAI pipeline
  query_policy(question)               — ChromaDB semantic search
  generate_eval_summary(candidate_id)  — sampling: LLM-written exec summary
  confirm_and_evaluate(resume_text)    — elicitation: confirm before pipeline run

PRIMITIVE 2 — RESOURCES  (data the LLM can read, static + parameterized)
  Static:
    schema://candidate                 — EvaluationResult JSON schema
    stats://evaluations                — aggregate disposition counts
    samples://resumes                  — list of sample resume files
    config://settings                  — current app config (no secrets)
  Parameterized templates:
    candidate://{candidate_id}         — one candidate as formatted markdown
    policy://{topic}                   — policy chunks for a topic keyword

PRIMITIVE 3 — PROMPTS  (reusable message templates)
  evaluate_resume(resume_text, role)   — multi-message trainer eval prompt
  policy_query(question)               — structured policy Q&A prompt
  disposition_review(candidate_id)     — fetch + format candidate for review

PRIMITIVE 4 — SAMPLING  (server asks the LLM to generate text)
  Used in: generate_eval_summary tool
  ctx.sample() sends candidate eval data to the connected LLM and returns
  a concise executive summary suitable for a hiring manager briefing.

PRIMITIVE 5 — ELICITATION  (server asks the user a question mid-tool)
  Used in: confirm_and_evaluate tool
  ctx.elicit() pauses the tool, presents a confirmation form to the user,
  and resumes only on accept — guarding the expensive pipeline run.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

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
async def confirm_and_evaluate(resume_text: str, ctx: Context, filename: str = "mcp_submission.txt") -> dict:
    """Submit a resume for evaluation — with elicitation-based confirmation gate.

    PRIMITIVE 5 — ELICITATION
    This tool demonstrates ctx.elicit(): before running the expensive LangGraph
    + CrewAI pipeline (30–120 seconds, LLM API calls), the server pauses and
    asks the user to confirm via a structured form.  If the user declines or
    cancels, the pipeline never runs.

    The elicitation form collects:
      - confirmed (bool): explicit go/no-go
      - priority (str): urgency hint passed to the pipeline log

    MCP protocol note: elicitation requires a client that supports it.
    MCP Inspector supports elicitation in stdio mode.

    Args:
        resume_text: Plain text resume content.
        filename: Display name for the submission (e.g. 'jane_doe.txt').

    Returns:
        EvaluationResult dict on success, or a status dict if declined/cancelled.
    """
    @dataclass
    class EvalConfirmation:
        confirmed: bool
        priority: str = "normal"  # "normal" | "urgent" | "low"

    preview = resume_text[:300].strip().replace("\n", " ")
    elicitation_result = await ctx.elicit(
        message=(
            f"Ready to run the full AI evaluation pipeline for **{filename}**.\n\n"
            f"Preview: _{preview}{'...' if len(resume_text) > 300 else ''}_\n\n"
            f"This will call Azure AI Foundry (gpt-4-1-mini), ChromaDB, and Brave Search. "
            f"Estimated time: 30–120 seconds.\n\n"
            f"Confirm to proceed."
        ),
        response_type=EvalConfirmation,
    )

    # Handle the three possible elicitation outcomes
    if elicitation_result.action != "accept":
        # DeclinedElicitation or CancelledElicitation
        return {
            "status": elicitation_result.action,
            "message": "Evaluation cancelled — pipeline was not run.",
        }

    data = elicitation_result.data
    if not data.confirmed:
        return {
            "status": "declined",
            "message": "User chose not to proceed with evaluation.",
        }

    await ctx.info(f"Evaluation confirmed (priority={data.priority}), starting pipeline...")

    from contoso_hr.watcher.process_resume import process_resume_text

    result = process_resume_text(resume_text, filename)
    if result is None:
        return {"error": "Evaluation failed — check server logs for details"}
    return result.model_dump()


@mcp.tool()
async def generate_eval_summary(candidate_id: str, ctx: Context) -> str:
    """Generate a hiring-manager executive summary for a candidate using LLM sampling.

    PRIMITIVE 4 — SAMPLING
    This tool demonstrates ctx.sample(): the MCP server sends a request back to
    the *connected LLM client* asking it to generate text.  The server provides
    structured candidate data; the client LLM writes the prose summary.  This
    inverts the normal flow — the server drives the LLM, not the other way around.

    The result is a concise 3-5 sentence briefing suitable for a hiring manager
    who has not read the full evaluation.

    Args:
        candidate_id: 8-char hex candidate identifier.

    Returns:
        LLM-generated executive summary string, or an error message.
    """
    store = _get_store()
    result = store.get_result(candidate_id)
    if result is None:
        return f"Candidate '{candidate_id}' not found."

    r = result
    eval_data = (
        f"Candidate: {r.candidate_name}\n"
        f"Disposition: {r.decision} (overall score {r.overall_score}/100)\n"
        f"Skills match: {r.skills_match_score}/100, Experience: {r.experience_score}/100\n"
        f"Strengths: {', '.join(r.strengths or []) or 'none recorded'}\n"
        f"Red flags: {', '.join(r.red_flags or []) or 'none identified'}\n"
        f"Reasoning: {r.reasoning or 'not recorded'}\n"
        f"Next steps: {'; '.join(r.next_steps or []) or 'none specified'}"
    )

    await ctx.info(f"Requesting LLM summary for candidate {candidate_id}")

    sampling_result = await ctx.sample(
        messages=(
            f"Write a concise 3–5 sentence executive summary of this candidate evaluation "
            f"for a hiring manager who has not read the full report. "
            f"Lead with the disposition and score, mention the top strength and top red flag, "
            f"and close with the recommended next step. Be direct and professional.\n\n"
            f"{eval_data}"
        ),
        system_prompt=(
            "You are a senior HR analyst at Contoso summarizing technical trainer "
            "candidate evaluations for busy hiring managers. Write in clear, professional prose."
        ),
        max_tokens=256,
    )

    return sampling_result.text or "Sampling returned no content."


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
# Resource Templates  (PRIMITIVE 2b — parameterized URIs)
#
# URI parameters map directly to function arguments.  FastMCP registers
# these as ResourceTemplates rather than static Resources, so clients can
# enumerate the template and instantiate it with concrete values.
# ---------------------------------------------------------------------------


@mcp.resource("candidate://{candidate_id}")
def candidate_resource(candidate_id: str) -> str:
    """Formatted markdown profile for a single evaluated candidate.

    URI example: candidate://a1b2c3d4

    Args:
        candidate_id: 8-char hex candidate identifier.

    Returns:
        Markdown-formatted evaluation summary, or an error message if not found.
    """
    store = _get_store()
    result = store.get_result(candidate_id)
    if result is None:
        return f"# Candidate Not Found\n\nNo evaluation exists for `{candidate_id}`."

    r = result
    lines = [
        f"# {r.candidate_name}",
        f"**ID:** `{r.candidate_id}`  |  **Decision:** {r.decision}  |  **Score:** {r.overall_score}/100",
        "",
        f"## Scores",
        f"- Skills match: {r.skills_match_score}/100",
        f"- Experience: {r.experience_score}/100",
        "",
        f"## Strengths",
        *[f"- {s}" for s in (r.strengths or [])],
        "",
        f"## Red Flags",
        *(([f"- {f}" for f in r.red_flags]) if r.red_flags else ["- None identified"]),
        "",
        f"## Reasoning",
        r.reasoning or "_No reasoning recorded._",
        "",
        f"## Recommended Next Steps",
        *[f"{i+1}. {s}" for i, s in enumerate(r.next_steps or [])],
        "",
        f"_Evaluated: {r.evaluated_at}_",
    ]
    return "\n".join(lines)


@mcp.resource("policy://{topic}")
def policy_topic_resource(topic: str) -> str:
    """HR policy chunks relevant to a topic keyword.

    URI example: policy://compensation  or  policy://mct-requirements

    Performs semantic search against ChromaDB and returns the top 3 matching
    policy chunks as plain text, each prefixed with its source document name.

    Args:
        topic: Keyword or short phrase describing the policy area of interest.

    Returns:
        Relevant policy text, or a message if no content is found.
    """
    from contoso_hr.knowledge.retriever import query_policy_knowledge

    context = query_policy_knowledge(topic, k=3)
    if not context.chunks:
        return f"No policy content found for topic: '{topic}'. Run `uv run hr-seed` to populate the knowledge base."

    parts = [f"# HR Policy: {topic}\n"]
    for chunk, source in zip(context.chunks, context.sources):
        parts.append(f"## [{source}]\n{chunk}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Prompts  (PRIMITIVE 3 — reusable message templates)
#
# Prompts return str (single user message), or list[dict] for multi-turn
# conversations with system context, user instructions, and assistant priming.
# FastMCP converts dict items to PromptMessage objects automatically.
# ---------------------------------------------------------------------------


@mcp.prompt()
def evaluate_resume(resume_text: str, role: str = "") -> list[dict]:
    """Multi-message prompt for structured trainer resume evaluation.

    Returns a system message establishing the evaluator persona, a user message
    with the resume and scoring rubric, and an assistant primer to guide output
    format.  The multi-message form gives the LLM clearer role separation than
    a single concatenated string.

    Args:
        resume_text: The resume content to evaluate.
        role: Optional target role (e.g. 'Senior Trainer — Azure Infrastructure').
              Defaults to 'Contoso technical trainer'.
    """
    role_label = role or "Contoso technical trainer"
    return [
        {
            "role": "user",
            "content": (
                f"You are a senior talent acquisition specialist at Contoso, evaluating "
                f"candidates for technical trainer roles covering Microsoft Azure, M365, "
                f"and Security certification courses.\n\n"
                f"Evaluate the following resume for the role of **{role_label}**.\n\n"
                f"Score each dimension 0–100 and recommend exactly one disposition:\n"
                f"- **Strong Match** (80+): Schedule interview immediately\n"
                f"- **Possible Match** (55–79): Schedule technical screen\n"
                f"- **Needs Review** (35–54): Recruiter follow-up needed\n"
                f"- **Not Qualified** (<35): Decline with courtesy\n\n"
                f"Evaluation criteria:\n"
                f"1. MCT (Microsoft Certified Trainer) status — required for Strong Match\n"
                f"2. Microsoft certifications: AZ-104, AZ-305, AZ-400, SC-300, AI-102\n"
                f"3. Training delivery volume and learner satisfaction (target 4.5+/5.0)\n"
                f"4. Curriculum development or course authorship experience\n"
                f"5. Hands-on technical depth in Azure/M365/Security\n\n"
                f"---\n\n{resume_text}"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "## Evaluation Summary\n\n"
                "**Skills Match Score:** \n"
                "**Experience Score:** \n"
                "**Overall Score:** \n"
                "**Disposition:** \n\n"
                "### Strengths\n- \n\n"
                "### Red Flags\n- \n\n"
                "### Reasoning\n\n"
                "### Recommended Next Steps\n1. "
            ),
        },
    ]


@mcp.prompt()
def policy_query(question: str) -> list[dict]:
    """Multi-message prompt for HR policy Q&A with grounding instruction.

    Returns a system-style user message that instructs the LLM to answer only
    from Contoso policy sources and cite the relevant section, followed by the
    actual question as a second user turn.

    Args:
        question: The HR policy question to answer.
    """
    return [
        {
            "role": "user",
            "content": (
                "You are the Contoso HR Policy Assistant. Answer questions accurately "
                "and concisely using only Contoso HR policy documentation. "
                "Always cite the relevant policy section or document name. "
                "If the answer is not covered by policy, say so explicitly — "
                "do not speculate."
            ),
        },
        {
            "role": "user",
            "content": f"Policy question: {question}",
        },
    ]


@mcp.prompt()
async def disposition_review(candidate_id: str, ctx: Context) -> list[dict]:
    """Fetch a candidate evaluation and format it as a review conversation.

    This prompt uses Context to log progress and reads live data from SQLite,
    so the LLM always receives the current evaluation state rather than a
    snapshot.  Useful for 'review this candidate and suggest interview questions'
    workflows.

    Args:
        candidate_id: 8-char hex candidate identifier.
    """
    await ctx.info(f"Loading candidate {candidate_id} for disposition review")

    store = _get_store()
    result = store.get_result(candidate_id)
    if result is None:
        return [
            {
                "role": "user",
                "content": f"Candidate `{candidate_id}` was not found in the database. Please verify the ID.",
            }
        ]

    r = result
    candidate_summary = (
        f"**Name:** {r.candidate_name}\n"
        f"**Decision:** {r.decision}  |  **Overall Score:** {r.overall_score}/100\n"
        f"**Skills Match:** {r.skills_match_score}/100  |  **Experience:** {r.experience_score}/100\n\n"
        f"**Strengths:** {', '.join(r.strengths or []) or 'None recorded'}\n"
        f"**Red Flags:** {', '.join(r.red_flags or []) or 'None identified'}\n\n"
        f"**Reasoning:** {r.reasoning or 'Not recorded'}\n\n"
        f"**Next Steps:** {'; '.join(r.next_steps or []) or 'None specified'}"
    )

    await ctx.info(f"Candidate loaded: {r.candidate_name} — {r.decision}")

    return [
        {
            "role": "user",
            "content": (
                "You are a Contoso hiring committee chair preparing for a candidate debrief. "
                "Review the evaluation below and provide: (1) a one-paragraph hiring rationale, "
                "(2) three targeted interview questions based on the red flags or experience gaps, "
                "and (3) any policy considerations relevant to this disposition.\n\n"
                f"## Candidate Evaluation\n\n{candidate_summary}"
            ),
        },
    ]
