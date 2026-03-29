"""
CrewAI Task factory functions for Contoso HR pipeline.

Open position: Microsoft Certified Trainer (MCT) delivering Azure, M365,
and Security certification courses at Contoso Learning.

Dispositions: Strong Match | Possible Match | Needs Review | Not Qualified
"""

from __future__ import annotations

from typing import Optional

from crewai import Agent, Task

from ..models import CandidateEval, PolicyContext, ResumeSubmission


def create_policy_expert_task(submission: ResumeSubmission, agent: Agent) -> Task:
    """PolicyExpert: assess candidate against Contoso HR policy for the MCT role."""
    return Task(
        description=f"""Assess this candidate against Contoso HR policy for the open
Microsoft Certified Trainer (MCT) position.

Candidate file: {submission.filename}

RESUME TEXT:
{submission.raw_text[:3000]}

Use the query_hr_policy tool to retrieve relevant policy before assessing. Search for:
- "minimum trainer qualifications"
- "MCT certification requirements"
- "compensation band trainer levels"
- "EEO hiring requirements"

Then assess:
1. Does the candidate meet Contoso's minimum qualifications for the MCT trainer role?
2. Any EEO/compliance considerations? (Process-related only — never candidate characteristics)
3. What trainer compensation level applies? (L1=Associate through L5=Principal Trainer)
4. Any policy flags (credential gaps, background check triggers)?

Output JSON with these exact keys:
{{
  "policy_context_summary": "2-3 sentence summary of relevant policy findings",
  "compliance_notes": ["list of specific policy considerations"],
  "recommended_level": "L1|L2|L3|L4|L5",
  "compensation_band": "e.g. $90,000–$130,000"
}}""",
        expected_output=(
            "JSON with policy_context_summary, compliance_notes, "
            "recommended_level, compensation_band"
        ),
        agent=agent,
    )


def create_resume_analyst_task(
    submission: ResumeSubmission,
    policy_context: Optional[PolicyContext],
    agent: Agent,
) -> Task:
    """ResumeAnalyst: score candidate qualifications for the open MCT position.

    policy_context is optional — this task runs in parallel with policy_expert
    so policy context may not be available yet. Falls back to standard policy text.
    """
    policy_summary = (
        policy_context.chunks[0][:500]
        if policy_context and policy_context.chunks
        else "Standard Contoso MCT trainer policy applies."
    )

    return Task(
        description=f"""Evaluate this candidate's fit for the open Microsoft Certified Trainer (MCT)
position at Contoso Learning. Contoso delivers Azure, M365, and Security certification courses.

Candidate file: {submission.filename}

POLICY CONTEXT (from HR Policy Expert):
{policy_summary}

RESUME TEXT:
{submission.raw_text[:3000]}

You may use brave_web_search to verify:
- MCT credential or certification validity
- Training organization credibility
- Current relevance of listed technical skills

Score on these MCT-specific dimensions (0-100 each):
- skills_match_score: Azure/M365/Security certification depth + practitioner credibility
  (Active MCT = strong signal; relevant cert stack multiplies the score)
- experience_score: Training delivery volume, learner satisfaction ratings, curriculum authorship

Extract:
- candidate_name: Full name from resume
- strengths: 2-4 specific standout qualities with evidence (cite session counts, ratings, certs)
- red_flags: 0-3 specific concerns (no MCT, expired certs, thin delivery history, gaps)
- recommended_role: Best-fit Contoso trainer title, e.g.:
    "Principal Trainer — Azure Security"
    "Senior Trainer — Azure Infrastructure"
    "Associate Trainer — M365"
    null if clearly not an MCT fit
- web_research_notes: What you searched and found (or "No web research performed")
- culture_fit_notes: 1-2 sentences on learner-focus, communication style, continuous learning

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
    """DecisionMaker: render final disposition for this MCT candidate."""
    strengths_str = "\n".join(f"  - {s}" for s in candidate_eval.strengths) or "  (none noted)"
    red_flags_str = "\n".join(f"  - {r}" for r in candidate_eval.red_flags) or "  (none noted)"
    policy_summary = (
        policy_context.chunks[0][:400] if policy_context.chunks
        else "Standard Contoso MCT trainer policy applies."
    )

    return Task(
        description=f"""Make the final screening disposition for this MCT candidate at Contoso Learning.

Open position: Microsoft Certified Trainer (MCT) — Azure, M365, and Security courses

Candidate: {submission.filename}
Recommended Role: {candidate_eval.recommended_role or "Not specified"}
Skills Match Score: {candidate_eval.skills_match_score}/100  (cert depth + practitioner credibility)
Experience Score:   {candidate_eval.experience_score}/100  (delivery volume + ratings + curriculum)

STRENGTHS:
{strengths_str}

RED FLAGS:
{red_flags_str}

POLICY COMPLIANCE CONTEXT:
{policy_summary}

CULTURE FIT:
{candidate_eval.culture_fit_notes}

Disposition thresholds for the MCT position:
- "Strong Match":   Active MCT, strong cert stack, proven delivery (100+ sessions or 4.7+ rating),
                    overall 80+. → Immediate interview.
- "Possible Match": MCT (active or near-term path) + solid certs + some delivery, or exceptional
                    practitioner with credible MCT plan. overall 55-79. → Technical screen.
- "Needs Review":   Promising but notable gaps — cert gaps, thin hours, unverifiable claims, or
                    unusual path. overall 35-54. → Recruiter follow-up before deciding.
- "Not Qualified":  No MCT path, no relevant Microsoft certs, no training experience, or policy
                    disqualifier. overall <35. → Decline.

Calculate overall_score = (skills_match_score × 0.5) + (experience_score × 0.5),
adjusted ±5 for exceptional strengths or serious red flags.

Output JSON with these exact keys:
{{
  "decision": "Strong Match|Possible Match|Needs Review|Not Qualified",
  "reasoning": "2-3 sentences grounded in the evidence above",
  "next_steps": ["2-4 specific actions, e.g. 'Schedule AZ-104 technical screen with hiring manager'"],
  "policy_compliance_notes": "string",
  "overall_score": 0-100
}}""",
        expected_output=(
            "JSON with decision (one of: Strong Match, Possible Match, Needs Review, Not Qualified), "
            "reasoning, next_steps, policy_compliance_notes, overall_score"
        ),
        agent=agent,
    )
