"""
CrewAI agent definitions for Contoso HR Agent.

Four agents covering the full hiring flow for the open MCT position:
  - ChatConciergeAgent  : Handles interactive chat, answers HR policy Q&A
  - PolicyExpertAgent   : Assesses policy compliance for each candidate
  - ResumeAnalystAgent  : Scores candidate fit for the MCT role (has web search tool)
  - DecisionMakerAgent  : Renders final disposition (Strong Match / Possible Match /
                          Needs Review / Not Qualified)

Pattern mirrors oreilly-agent-mvp/crew_variant/agents.py:
  Each class has ROLE, GOAL, BACKSTORY, and a create() classmethod.
"""

from __future__ import annotations

from crewai import Agent, LLM

from .prompts import (
    CHAT_CONCIERGE_SYSTEM_PROMPT,
    DECISION_MAKER_SYSTEM_PROMPT,
    POLICY_EXPERT_SYSTEM_PROMPT,
    RESUME_ANALYST_SYSTEM_PROMPT,
)
from .tools import get_policy_expert_tools, get_resume_analyst_tools


class ChatConciergeAgent:
    """Alex — Contoso HR Chat Concierge for interactive Q&A.

    Uses the query_hr_policy tool so every policy answer is grounded
    in ChromaDB-retrieved Contoso documentation, not LLM hallucination.
    Invoked by engine.py /api/chat instead of a raw LLM call.
    """

    ROLE = "Contoso HR Chat Concierge"
    GOAL = (
        "Help recruiters and hiring managers with the MCT hiring process — "
        "answer HR policy questions accurately using Contoso documentation, "
        "guide users through resume submission, and explain evaluation results."
    )
    BACKSTORY = CHAT_CONCIERGE_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the Chat Concierge agent with policy retrieval tool.

        Args:
            llm: CrewAI LLM instance (from Config.get_crew_llm()).

        Returns:
            Configured CrewAI Agent.
        """
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=llm,
            tools=get_policy_expert_tools(),  # query_hr_policy (ChromaDB)
            verbose=False,  # chat responses don't need verbose crew output
            allow_delegation=False,
        )


class PolicyExpertAgent:
    """HR Policy Expert who retrieves and applies Contoso HR policies."""

    ROLE = "Contoso HR Policy Expert"
    GOAL = (
        "Ensure all MCT hiring decisions comply with Contoso HR policy, EEO requirements, "
        "and compensation guidelines by retrieving and applying policy documentation."
    )
    BACKSTORY = POLICY_EXPERT_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the PolicyExpert agent with policy retrieval tool."""
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=llm,
            tools=get_policy_expert_tools(),
            verbose=True,
            allow_delegation=False,
        )


class ResumeAnalystAgent:
    """Senior Talent Acquisition Specialist who evaluates MCT candidate qualifications."""

    ROLE = "Senior Talent Acquisition Specialist"
    GOAL = (
        "Objectively evaluate candidates' MCT credentials, cert stack, delivery track record, "
        "and technical depth for the open Microsoft Certified Trainer position at Contoso. "
        "Provide scored, evidence-based assessments."
    )
    BACKSTORY = RESUME_ANALYST_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the ResumeAnalyst agent with web search tool."""
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=llm,
            tools=get_resume_analyst_tools(),
            verbose=True,
            allow_delegation=False,
        )


class DecisionMakerAgent:
    """Hiring Committee Chair who renders the final MCT screening disposition."""

    ROLE = "Hiring Committee Chair"
    GOAL = (
        "Synthesize the HR policy assessment and candidate evaluation into a clear "
        "screening disposition for the MCT position: "
        "Strong Match, Possible Match, Needs Review, or Not Qualified."
    )
    BACKSTORY = DECISION_MAKER_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the DecisionMaker agent (no external tools — pure reasoning)."""
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=llm,
            tools=[],
            verbose=True,
            allow_delegation=False,
        )
