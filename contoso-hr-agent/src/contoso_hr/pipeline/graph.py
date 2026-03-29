"""
LangGraph StateGraph for Contoso HR Agent pipeline.

Architecture: LangGraph owns WHEN and STATE. CrewAI owns WHO and WHAT.
Each *_crew_node runs exactly one Crew.kickoff() call.

Graph flow (parallel fan-out / fan-in):

  [intake]
     ├──→ [policy_expert]  ──┐
     └──→ [resume_analyst] ──┴──→ [decision_maker] → [notify] → END

policy_expert and resume_analyst run concurrently — they are independent:
  - policy_expert: queries ChromaDB for HR policy compliance
  - resume_analyst: scores qualifications + optional Brave web research
Both feed into decision_maker, which waits for both to complete before
rendering the final disposition.

IMPORTANT: parallel nodes must return ONLY the keys they write, not
{**state, ...}. LangGraph merges partial updates at the fan-in point.

Checkpointing via SqliteSaver enables cross-run memory per session_id (thread_id).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional, TypedDict
from uuid import uuid4

from crewai import Crew, Process
from langgraph.graph import END, StateGraph

from ..config import get_config
from ..logging_setup import get_hr_logger
from ..models import (
    CandidateEval,
    EvaluationResult,
    HRDecision,
    PolicyContext,
    ResumeSubmission,
)
from .agents import DecisionMakerAgent, PolicyExpertAgent, ResumeAnalystAgent
from .tasks import (
    create_decision_maker_task,
    create_policy_expert_task,
    create_resume_analyst_task,
)


# =============================================================================
# Pipeline State
# =============================================================================


class HRState(TypedDict, total=False):
    """State passed through all LangGraph nodes.

    All Pydantic model fields are stored as serialized dicts (model_dump())
    for LangGraph checkpoint compatibility.
    """

    session_id: str
    run_id: str
    start_time: float

    # Input
    resume: Optional[dict]           # serialized ResumeSubmission

    # Agent outputs (serialized Pydantic models)
    policy_context: Optional[dict]   # serialized PolicyContext
    policy_meta: Optional[dict]      # raw dict from PolicyExpert crew output
    candidate_eval: Optional[dict]   # serialized CandidateEval
    hr_decision: Optional[dict]      # serialized HRDecision

    # Final
    result: Optional[dict]           # serialized EvaluationResult
    error: Optional[str]


# =============================================================================
# Node Functions
# =============================================================================


def intake_node(state: HRState) -> HRState:
    """Validate the incoming ResumeSubmission.

    Node 1: Parses and validates resume data, sets run metadata.
    """
    logger = get_hr_logger()
    logger.node_enter("intake")

    resume_data = state.get("resume")
    if not resume_data:
        return {**state, "error": "No resume data in state"}

    try:
        submission = ResumeSubmission(**resume_data)
        logger.agent_message("system", f"Processing: {submission.filename}")
        logger.node_exit("intake", f"{len(submission.raw_text)} chars")
    except Exception as e:
        return {**state, "error": f"Invalid resume data: {e}"}

    return state


def policy_expert_crew_node(state: HRState) -> HRState:
    """PolicyExpert agent assesses resume against Contoso HR policy.

    Parallel branch A: Single CrewAI Crew with PolicyExpertAgent + query_hr_policy tool.
    Returns only its own keys — LangGraph merges with resume_analyst output at fan-in.
    """
    logger = get_hr_logger()
    logger.node_enter("policy_expert")

    if state.get("error"):
        return {}

    try:
        submission = ResumeSubmission(**state["resume"])
        config = get_config()
        llm = config.get_crew_llm()

        agent = PolicyExpertAgent.create(llm)
        task = create_policy_expert_task(submission, agent)

        logger.agent_message("policy", "Assessing against Contoso HR policy...")
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()

        raw_data = _extract_json(result.raw)
        if raw_data is None:
            logger.warning("PolicyExpert output was not JSON — using fallback")
            raw_data = {
                "policy_context_summary": str(result.raw)[:500],
                "compliance_notes": ["Review policy expert output manually"],
                "recommended_level": "L3",
                "compensation_band": "See HR",
            }

        policy_context = PolicyContext(
            chunks=[raw_data.get("policy_context_summary", "")],
            sources=["policy_expert_crew"],
            query="resume policy assessment",
        )

        logger.node_exit("policy_expert", raw_data.get("recommended_level", ""))
        # Return ONLY this node's keys — parallel merge requires partial updates
        return {
            "policy_context": policy_context.model_dump(),
            "policy_meta": raw_data,
        }

    except Exception as e:
        logger.error(f"PolicyExpert crew failed: {e}", e)
        return {"error": f"PolicyExpert crew failed: {e}"}


def resume_analyst_crew_node(state: HRState) -> HRState:
    """ResumeAnalyst agent scores the candidate with optional web research.

    Parallel branch B: Single CrewAI Crew with ResumeAnalystAgent + brave_web_search tool.
    Runs concurrently with policy_expert — does NOT read policy_context from state
    (it hasn't been written yet). policy_context is merged in at decision_maker.
    Returns only its own keys — LangGraph merges with policy_expert output at fan-in.
    """
    logger = get_hr_logger()
    logger.node_enter("resume_analyst")

    if state.get("error"):
        return {}

    try:
        submission = ResumeSubmission(**state["resume"])
        config = get_config()
        llm = config.get_crew_llm()

        agent = ResumeAnalystAgent.create(llm)
        # policy_context=None — running in parallel, not yet available
        task = create_resume_analyst_task(submission, None, agent)

        logger.agent_message("analyst", "Evaluating candidate qualifications...")
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()

        raw_data = _extract_json(result.raw)
        if raw_data is None:
            logger.warning("ResumeAnalyst output was not JSON — using fallback")
            raw_data = {
                "candidate_name": "Unknown",
                "skills_match_score": 50,
                "experience_score": 50,
                "culture_fit_notes": "Unable to parse analyst output",
                "red_flags": [],
                "strengths": [str(result.raw)[:200]],
                "recommended_role": None,
                "web_research_notes": "Parse error",
            }

        candidate_eval = CandidateEval(
            skills_match_score=raw_data.get("skills_match_score", 50),
            experience_score=raw_data.get("experience_score", 50),
            culture_fit_notes=raw_data.get("culture_fit_notes", ""),
            red_flags=raw_data.get("red_flags", []),
            strengths=raw_data.get("strengths", []),
            recommended_role=raw_data.get("recommended_role"),
            web_research_notes=raw_data.get("web_research_notes", ""),
            candidate_name=raw_data.get("candidate_name"),
        )

        logger.node_exit(
            "resume_analyst",
            f"skills={candidate_eval.skills_match_score} exp={candidate_eval.experience_score}",
        )
        # Return ONLY this node's keys — parallel merge requires partial updates
        return {"candidate_eval": candidate_eval.model_dump()}

    except Exception as e:
        logger.error(f"ResumeAnalyst crew failed: {e}", e)
        return {"error": f"ResumeAnalyst crew failed: {e}"}


def decision_maker_crew_node(state: HRState) -> HRState:
    """DecisionMaker agent renders the final MCT screening disposition.

    Node 4: Single CrewAI Crew with DecisionMakerAgent (no external tools).
    Pure reasoning over prior agent outputs.
    """
    logger = get_hr_logger()
    logger.node_enter("decision_maker")

    if state.get("error"):
        return state

    try:
        submission = ResumeSubmission(**state["resume"])
        policy_context = PolicyContext(**state["policy_context"])
        candidate_eval = CandidateEval(**state["candidate_eval"])
        config = get_config()
        llm = config.get_crew_llm()

        agent = DecisionMakerAgent.create(llm)
        task = create_decision_maker_task(submission, policy_context, candidate_eval, agent)

        logger.agent_message("decision", "Rendering hiring decision...")
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()

        raw_data = _extract_json(result.raw)
        if raw_data is None:
            logger.warning("DecisionMaker output was not JSON — using fallback")
            avg_score = (
                candidate_eval.skills_match_score + candidate_eval.experience_score
            ) // 2
            raw_data = {
                "decision": "Needs Review",
                "reasoning": str(result.raw)[:400],
                "next_steps": ["Manual review required — automated decision parsing failed"],
                "policy_compliance_notes": "Automated disposition failed; manual review needed",
                "overall_score": avg_score,
            }

        hr_decision = HRDecision(
            decision=raw_data.get("decision", "Needs Review"),
            reasoning=raw_data.get("reasoning", ""),
            next_steps=raw_data.get("next_steps", []),
            policy_compliance_notes=raw_data.get("policy_compliance_notes", ""),
            overall_score=raw_data.get("overall_score", 50),
        )

        logger.node_exit("decision_maker", hr_decision.decision.upper())
        return {**state, "hr_decision": hr_decision.model_dump()}

    except Exception as e:
        logger.error(f"DecisionMaker crew failed: {e}", e)
        return {**state, "error": f"DecisionMaker crew failed: {e}"}


def notify_node(state: HRState) -> HRState:
    """Assemble the final EvaluationResult and log completion.

    Node 5: No LLM calls. Assembles EvaluationResult from all prior outputs.
    Persistence (SQLite write) happens in process_resume.py after graph returns.
    """
    logger = get_hr_logger()
    logger.node_enter("notify")

    if state.get("error"):
        # Create a minimal error result
        error_result = {
            "candidate_id": state.get("session_id", str(uuid4())[:8]),
            "run_id": state.get("run_id", str(uuid4())),
            "filename": state.get("resume", {}).get("filename", "unknown"),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "candidate_name": "Unknown",
            "candidate_eval": {
                "skills_match_score": 0, "experience_score": 0,
                "culture_fit_notes": "", "red_flags": [state["error"]],
                "strengths": [], "recommended_role": None, "web_research_notes": "",
            },
            "hr_decision": {
                "decision": "Needs Review",
                "reasoning": f"Pipeline error: {state['error']}",
                "next_steps": ["Manual review required — pipeline did not complete"],
                "policy_compliance_notes": "",
                "overall_score": 0,
            },
            "policy_context_summary": "",
            "duration_seconds": time.time() - state.get("start_time", time.time()),
        }
        logger.node_exit("notify", "error result")
        return {**state, "result": error_result}

    try:
        submission = ResumeSubmission(**state["resume"])
        candidate_eval = CandidateEval(**state["candidate_eval"])
        hr_decision = HRDecision(**state["hr_decision"])
        policy_meta = state.get("policy_meta", {})

        duration = None
        if "start_time" in state:
            duration = time.time() - state["start_time"]

        # Extract candidate name from eval (analyst parsed it from resume)
        candidate_name = (
            candidate_eval.candidate_name
            or submission.filename.replace("_", " ").replace(".txt", "").replace("-", " ").title()
        )

        result = EvaluationResult(
            candidate_id=submission.candidate_id,
            run_id=state.get("run_id", str(uuid4())),
            filename=submission.filename,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            candidate_name=candidate_name,
            candidate_eval=candidate_eval,
            hr_decision=hr_decision,
            policy_context_summary=policy_meta.get("policy_context_summary", ""),
            duration_seconds=duration,
        )

        logger.complete_run(
            run_id=result.run_id,
            candidate_id=result.candidate_id,
            decision=result.decision,
            output_file=f"data/outgoing/{result.candidate_id}.json",
            duration=duration,
        )

        return {**state, "result": result.model_dump()}

    except Exception as e:
        logger.error(f"Notify node failed: {e}", e)
        return {**state, "error": f"Notify failed: {e}"}


# =============================================================================
# Graph Builder
# =============================================================================


def create_hr_graph(data_dir: Path):
    """Build and compile the HR evaluation LangGraph StateGraph.

    Uses SqliteSaver checkpointing so state persists across runs.
    Pass config={"configurable": {"thread_id": session_id}} to graph.invoke()
    to enable per-session memory.

    Args:
        data_dir: Directory for checkpoints.db (usually data/).

    Returns:
        Compiled LangGraph StateGraph.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(data_dir / "checkpoints.db"), check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    builder = StateGraph(HRState)

    builder.add_node("intake", intake_node)
    builder.add_node("policy_expert", policy_expert_crew_node)
    builder.add_node("resume_analyst", resume_analyst_crew_node)
    builder.add_node("decision_maker", decision_maker_crew_node)
    builder.add_node("notify", notify_node)

    # Fan-out: intake spawns both specialist agents concurrently
    builder.set_entry_point("intake")
    builder.add_edge("intake", "policy_expert")
    builder.add_edge("intake", "resume_analyst")

    # Fan-in: decision_maker waits for BOTH branches to complete
    builder.add_edge("policy_expert", "decision_maker")
    builder.add_edge("resume_analyst", "decision_maker")

    builder.add_edge("decision_maker", "notify")
    builder.add_edge("notify", END)

    return builder.compile(checkpointer=checkpointer)


# =============================================================================
# Helpers
# =============================================================================


def _extract_json(text: str) -> Optional[dict]:
    """Extract a JSON dict from CrewAI output text.

    Tries: direct parse → markdown code block → raw brace-delimited object.
    """
    if not text:
        return None

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown code blocks
    for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    # Last-resort: find outermost braces
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None
