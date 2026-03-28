"""
Unit tests for pipeline components (no LLM calls).
Tests graph state handling, JSON extraction, and model integration.
"""

import pytest

from contoso_hr.pipeline.graph import HRState, _extract_json


class TestExtractJson:
    def test_pure_json(self):
        text = '{"decision": "advance", "score": 85}'
        result = _extract_json(text)
        assert result == {"decision": "advance", "score": 85}

    def test_markdown_json_block(self):
        text = '```json\n{"decision": "hold", "score": 50}\n```'
        result = _extract_json(text)
        assert result is not None
        assert result["decision"] == "hold"

    def test_json_in_prose(self):
        text = 'After careful analysis, the result is: {"verdict": "pass", "items": [1, 2, 3]}'
        result = _extract_json(text)
        assert result is not None
        assert result["verdict"] == "pass"

    def test_invalid_json_returns_none(self):
        result = _extract_json("This is just plain text with no JSON")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _extract_json("")
        assert result is None

    def test_nested_json(self):
        text = '{"outer": {"inner": "value"}, "list": [1, 2]}'
        result = _extract_json(text)
        assert result["outer"]["inner"] == "value"


class TestHRStateStructure:
    def test_state_is_typeddict(self):
        """HRState is a TypedDict — verify required fields can be set."""
        state: HRState = {
            "session_id": "test-session",
            "run_id": "run-001",
            "start_time": 0.0,
        }
        assert state["session_id"] == "test-session"

    def test_state_with_error(self):
        state: HRState = {
            "session_id": "s1",
            "error": "Something went wrong",
        }
        assert state.get("error") == "Something went wrong"
        assert state.get("resume") is None  # total=False means optional


class TestPipelineTools:
    """Test @tool functions don't raise on missing config (graceful fallback)."""

    def test_query_hr_policy_fallback_no_chroma(self, tmp_path):
        """query_hr_policy returns a fallback message when ChromaDB is empty."""
        from unittest.mock import patch

        from contoso_hr.pipeline.tools import query_hr_policy

        # Patch retriever to return empty context
        from contoso_hr.models import PolicyContext

        with patch(
            "contoso_hr.pipeline.tools.query_policy_knowledge",
            return_value=PolicyContext(chunks=[], sources=[], query="test"),
        ):
            result = query_hr_policy.run("What is the EEO policy?")
            assert "No relevant" in result or "policy" in result.lower()

    def test_brave_web_search_no_key(self, monkeypatch):
        """brave_web_search returns a graceful message when no API key is set."""
        import os

        from contoso_hr.pipeline.tools import brave_web_search

        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        result = brave_web_search.run("Azure certification requirements")
        assert "not configured" in result.lower() or "results" in result.lower()
