"""
CrewAI @tool functions for Contoso HR Agent pipeline.

Tools are injected into CrewAI Agent instances so the LLM can call them
during Crew.kickoff() task execution.

Tools:
  - query_hr_policy: ChromaDB semantic search over HR policy docs
  - brave_web_search: Brave Search API for candidate/company research
"""

from __future__ import annotations

import json
import os
from typing import Optional

import httpx
from crewai.tools import tool

from ..knowledge.retriever import query_policy_knowledge


@tool("query_hr_policy")
def query_hr_policy(question: str) -> str:
    """Query the Contoso HR policy knowledge base using semantic search.

    Use this tool to look up Contoso HR policies before making any
    policy-related assessment. Never guess at policy details.

    Args:
        question: Natural language question about HR policy.
                  Examples: 'What are the minimum qualifications policy?',
                  'What is the compensation band for Level 3?',
                  'What does the EEO policy say about interview topics?'

    Returns:
        Relevant policy text chunks from the knowledge base.
    """
    try:
        context = query_policy_knowledge(question, k=4)
        if not context.chunks:
            return "No relevant policy content found. Please consult HR directly."

        parts = []
        for chunk, source in zip(context.chunks, context.sources):
            parts.append(f"[Source: {source}]\n{chunk}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Policy knowledge base query failed: {e}. Proceed with general knowledge."


@tool("brave_web_search")
def brave_web_search(query: str) -> str:
    """Search the web for candidate verification or background research.

    Use for verifying company existence, technology relevance, certification
    programs, or industry context. Do not use for personal information lookups.

    Args:
        query: Search query string.
               Examples: 'Microsoft AZ-305 certification requirements',
               'Northwind Traders Seattle technology company',
               'Azure Kubernetes Service current best practices'

    Returns:
        JSON string with up to 5 search results (title, url, description).
    """
    api_key = os.getenv("BRAVE_API_KEY", "")
    if not api_key:
        return json.dumps({
            "note": "Brave Search not configured (BRAVE_API_KEY not set). "
                    "Proceeding without web search.",
            "results": [],
        })

    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 5, "text_decorations": False},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", "")[:300],
            })

        return json.dumps({"query": query, "results": results}, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"Search API error: {e.response.status_code}", "results": []})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


def get_policy_expert_tools() -> list:
    """Tools for the PolicyExpert agent."""
    return [query_hr_policy]


def get_resume_analyst_tools() -> list:
    """Tools for the ResumeAnalyst agent."""
    return [brave_web_search]
