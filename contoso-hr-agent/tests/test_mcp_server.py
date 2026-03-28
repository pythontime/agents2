"""
Unit tests for the FastMCP 2 server (no LLM calls).
Tests that tools, resources, and prompts are registered correctly.
"""

import pytest


class TestMCPServerRegistration:
    """Verify tools, resources, and prompts are registered with FastMCP 2."""

    def test_server_has_correct_name(self):
        from contoso_hr.mcp_server.server import mcp
        assert mcp.name == "contoso-hr-agent"

    def test_tools_registered(self):
        from contoso_hr.mcp_server.server import mcp
        # FastMCP 2 exposes tools via _tool_manager or list_tools()
        # Try both API surfaces
        tool_names = set()
        try:
            tool_names = {t.name for t in mcp.list_tools()}
        except (AttributeError, TypeError):
            # Alternative: inspect _tool_manager
            try:
                tool_names = set(mcp._tool_manager._tools.keys())
            except AttributeError:
                pass

        expected = {"get_candidate", "list_candidates", "trigger_resume_evaluation", "query_policy"}
        for name in expected:
            assert name in tool_names, f"Tool '{name}' not registered in MCP server"

    def test_resources_registered(self):
        from contoso_hr.mcp_server.server import mcp
        resource_uris = set()
        try:
            resources = mcp.list_resources()
            resource_uris = {str(r.uri) for r in resources}
        except (AttributeError, TypeError):
            try:
                resource_uris = set(mcp._resource_manager._resources.keys())
            except AttributeError:
                pass

        expected_uris = {"schema://candidate", "stats://evaluations"}
        for uri in expected_uris:
            assert uri in resource_uris, f"Resource '{uri}' not registered in MCP server"

    def test_prompts_registered(self):
        from contoso_hr.mcp_server.server import mcp
        prompt_names = set()
        try:
            prompts = mcp.list_prompts()
            prompt_names = {p.name for p in prompts}
        except (AttributeError, TypeError):
            try:
                prompt_names = set(mcp._prompt_manager._prompts.keys())
            except AttributeError:
                pass

        expected = {"evaluate_resume", "policy_query"}
        for name in expected:
            assert name in prompt_names, f"Prompt '{name}' not registered in MCP server"


class TestMCPPrompts:
    """Test prompt content generation (no I/O)."""

    def test_evaluate_resume_prompt(self):
        from contoso_hr.mcp_server.server import evaluate_resume
        result = evaluate_resume("Alice Zhang — Senior Engineer", role="Cloud Architect")
        assert "Cloud Architect" in result
        assert "Alice Zhang" in result
        assert "Contoso" in result

    def test_evaluate_resume_no_role(self):
        from contoso_hr.mcp_server.server import evaluate_resume
        result = evaluate_resume("Some resume text")
        assert "resume" in result.lower()
        assert "Some resume text" in result

    def test_policy_query_prompt(self):
        from contoso_hr.mcp_server.server import policy_query
        result = policy_query("What is the salary band for Level 3?")
        assert "Level 3" in result
        assert "Contoso" in result


class TestMCPPortUtils:
    """Test port management utilities."""

    def test_force_kill_port_does_not_raise_on_free_port(self):
        """Killing a port with no listener should not raise."""
        from contoso_hr.util.port_utils import force_kill_port
        # Port 19999 is very unlikely to be in use
        force_kill_port(19999)  # should complete without exception

    def test_wait_for_port_free_returns_true_for_free_port(self):
        from contoso_hr.util.port_utils import wait_for_port_free
        assert wait_for_port_free(19999, timeout_seconds=1.0) is True
