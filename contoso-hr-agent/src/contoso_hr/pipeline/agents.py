"""
CrewAI agent definitions for Contoso HR Agent.

Three agents, each with a distinct HR persona:
  - PolicyExpertAgent: Knows Contoso HR policy via ChromaDB RAG
  - ResumeAnalystAgent: Evaluates candidate qualifications (has web search tool)
  - DecisionMakerAgent: Synthesizes inputs into advance/hold/reject decision

Pattern mirrors oreilly-agent-mvp/crew_variant/agents.py:
  Each agent class has ROLE, GOAL, BACKSTORY, and a create() classmethod.
"""

from __future__ import annotations

from crewai import Agent, LLM

from .prompts import (
    DECISION_MAKER_SYSTEM_PROMPT,
    POLICY_EXPERT_SYSTEM_PROMPT,
    RESUME_ANALYST_SYSTEM_PROMPT,
)
from .tools import get_policy_expert_tools, get_resume_analyst_tools


class PolicyExpertAgent:
    """HR Policy Expert who retrieves and applies Contoso HR policies."""

    ROLE = "Contoso HR Policy Expert"
    GOAL = (
        "Ensure all hiring decisions comply with Contoso HR policy, EEO requirements, "
        "and compensation guidelines by retrieving and applying policy documentation."
    )
    BACKSTORY = POLICY_EXPERT_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the PolicyExpert agent with policy retrieval tools.

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
            tools=get_policy_expert_tools(),
            verbose=True,
            allow_delegation=False,
        )


class ResumeAnalystAgent:
    """Senior Technical Recruiter who evaluates candidate qualifications."""

    ROLE = "Senior Technical Recruiter"
    GOAL = (
        "Objectively evaluate candidates' technical skills, experience depth, and career trajectory "
        "using resume content and web research. Provide scored, evidence-based assessments."
    )
    BACKSTORY = RESUME_ANALYST_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the ResumeAnalyst agent with web search tool.

        Args:
            llm: CrewAI LLM instance.

        Returns:
            Configured CrewAI Agent.
        """
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
    """Hiring Committee Chair who makes the final advance/hold/reject decision."""

    ROLE = "Hiring Committee Chair"
    GOAL = (
        "Synthesize HR policy compliance assessment and candidate evaluation into a clear, "
        "justified hiring decision (advance/hold/reject) with concrete next steps."
    )
    BACKSTORY = DECISION_MAKER_SYSTEM_PROMPT

    @classmethod
    def create(cls, llm: LLM) -> Agent:
        """Create the DecisionMaker agent (no external tools — pure reasoning).

        Args:
            llm: CrewAI LLM instance.

        Returns:
            Configured CrewAI Agent.
        """
        return Agent(
            role=cls.ROLE,
            goal=cls.GOAL,
            backstory=cls.BACKSTORY,
            llm=llm,
            tools=[],
            verbose=True,
            allow_delegation=False,
        )
