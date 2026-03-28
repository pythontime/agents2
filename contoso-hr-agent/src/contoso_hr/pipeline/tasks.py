"""
CrewAI Task factory functions for Contoso HR pipeline.

Contoso hires technical trainers for Microsoft Azure, M365, and Security
certification courses. Tasks are scoped accordingly: MCT status, Azure certs,
delivery hours, and learner satisfaction are the primary evaluation signals.

Pattern mirrors oreilly-agent-mvp/crew_variant/tasks.py.
"""

from __future__ import annotations

from crewai import Agent, Task

from ..models import CandidateEval, PolicyContext, ResumeSubmission


def create_policy_expert_task(submission: ResumeSubmission, agent: Agent) -> Task:
    """PolicyExpert: assess candidate against Contoso HR policy."""
    return Task(
        description=f"""Assess this trainer candidate against Contoso HR hiring policy.

Candidate file: {submission.filename}

RESUME TEXT:
{submission.raw_text[:3000]}

Use the query_hr_policy tool to retrieve relevant Contoso HR policy before assessing.
Search for:
- "minimum trainer qualifications"
- "MCT certification requirements"
- "compensation band trainer levels"
- "EEO hiring requirements"

Then assess:
1. Does the candidate appear to meet Contoso's minimum qualifications for a trainer role?
   (Check for MCT status, relevant Microsoft certifications, delivery experience thresholds)
2. Any EEO/compliance considerations? (Process-related only — never candidate characteristics)
3. What compensation level applies? (L1=Associate Trainer through L5=Principal Trainer)
4. Any policy-relevant notes (credential gaps, background check triggers)?

Output JSON with these exact keys:
{{
  "policy_context_summary": "2-3 sentence summary of policy findings",
  "compliance_notes": ["list of specific policy considerations"],
  "recommended_level": "L1|L2|L3|L4|L5",
  "compensation_band": "string (e.g. $90,000–$130,000)"
}}""",
        expected_output=(
            "JSON with policy_context_summary, compliance_notes, "
            "recommended_level, compensation_band"
        ),
        agent=agent,
    )


def create_resume_analyst_task(
    submission: ResumeSubmission,
    policy_context: PolicyContext,
    agent: Agent,
) -> Task:
    """ResumeAnalyst: evaluate trainer qualifications and delivery track record."""
    policy_summary = (
        policy_context.chunks[0][:500] if policy_context.chunks
        else "No policy context available."
    )

    return Task(
        description=f"""Evaluate this candidate's qualifications for a technical trainer role at Contoso.

Contoso delivers Microsoft Azure, M365, and Security certification training.

Candidate file: {submission.filename}

POLICY CONTEXT (from HR Policy Expert):
{policy_summary}

RESUME TEXT:
{submission.raw_text[:3000]}

You may use brave_web_search to verify:
- MCT status or Microsoft certification legitimacy
- Whether training organizations (e.g., Opsgility, Pluralsight, Global Knowledge) are credible
- Current relevance of technical skills listed

Score on these dimensions (0-100 each):
- skills_match_score: Azure/M365/Security certification depth + hands-on technical credibility
  (MCT = strong signal; no certs = low score regardless of experience)
- experience_score: Training delivery volume, learner ratings, curriculum development, years

Extract:
- candidate_name: Full name from resume
- strengths: 2-4 specific standout qualities with evidence (cite numbers: sessions, ratings, certs)
- red_flags: 0-3 concerns (missing MCT, no delivery stats, expired certs, thin experience)
- recommended_role: Most appropriate Contoso trainer title
  (e.g., "Associate Trainer", "Senior Trainer — Azure Infrastructure",
   "Principal Trainer — Security", or null if clearly not a trainer fit)
- web_research_notes: What you searched and found (or "No web research performed")
- culture_fit_notes: 1-2 sentences on communication style, learner-focus, continuous learning signals

Output JSON with these exact keys:
{{
  "candidate_name": "string",
  "skills_match_score": 0-100,
  "experience_score": 0-100,
  "culture_fit_notes": "string",
  "red_flags": ["list"],
  "strengths": ["list"],
  "recommended_role": "string or null",
  "web_research_notes": "string"
}}""",
        expected_output=(
            "JSON with candidate_name, skills_match_score, experience_score, "
            "culture_fit_notes, red_flags, strengths, recommended_role, web_research_notes"
        ),
        agent=agent,
    )


def create_decision_maker_task(
    submission: ResumeSubmission,
    policy_context: PolicyContext,
    candidate_eval: CandidateEval,
    agent: Agent,
) -> Task:
    """DecisionMaker: render final advance/hold/reject for this trainer candidate."""
    strengths_str = "\n".join(f"  - {s}" for s in candidate_eval.strengths) or "  (none)"
    red_flags_str = "\n".join(f"  - {r}" for r in candidate_eval.red_flags) or "  (none)"
    policy_summary = (
        policy_context.chunks[0][:400] if policy_context.chunks
        else "Standard Contoso trainer policy applies."
    )

    return Task(
        description=f"""Make the final hiring decision for this trainer candidate at Contoso.

Candidate: {submission.filename}
Recommended Role: {candidate_eval.recommended_role or "Not specified"}
Skills Match Score: {candidate_eval.skills_match_score}/100
  (Azure/M365/Security cert depth + hands-on credibility)
Experience Score: {candidate_eval.experience_score}/100
  (delivery volume, learner ratings, curriculum development)

STRENGTHS:
{strengths_str}

RED FLAGS:
{red_flags_str}

POLICY COMPLIANCE CONTEXT:
{policy_summary}

CULTURE FIT:
{candidate_eval.culture_fit_notes}

Decision guidance for Contoso trainer roles:
- "advance": MCT (or clear MCT path + strong certs), proven delivery record, overall 65+
- "hold": Solid technical base but cert gaps, limited delivery hours, or needs credential verification
- "reject": No relevant Microsoft certs, no training experience, policy disqualifier, or overall <35

Calculate overall_score = (skills_match_score × 0.5) + (experience_score × 0.5),
adjusted ±5 for exceptional strengths or serious red flags.

Output JSON with these exact keys:
{{
  "decision": "advance|hold|reject",
  "reasoning": "2-3 sentences grounded in the evidence above",
  "next_steps": ["2-4 specific actions, e.g. 'Schedule AZ-104 technical screen'"],
  "policy_compliance_notes": "string",
  "overall_score": 0-100
}}""",
        expected_output=(
            "JSON with decision, reasoning, next_steps, policy_compliance_notes, overall_score"
        ),
        agent=agent,
    )
