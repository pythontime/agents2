"""
Contoso HR Agent MCP Server entry point.

Kills port MCP_PORT (default 8081) before starting to ensure clean bind.
Starts FastMCP 2 with SSE transport.

Connect MCP Inspector to: http://localhost:8081/sse
"""

from __future__ import annotations


def main() -> None:
    """Kill MCP_PORT, then start FastMCP 2 SSE server."""
    from contoso_hr.config import get_config
    from contoso_hr.logging_setup import console, setup_logging
    from contoso_hr.util.port_utils import force_kill_port

    config = get_config()
    setup_logging(config.log_level)

    port = config.mcp_port
    force_kill_port(port)

    console.print(f"\n[bold cyan]Contoso HR MCP Server[/]")
    console.print(f"  SSE endpoint: [link]http://localhost:{port}/sse[/]")
    console.print(f"  MCP Inspector: npx @modelcontextprotocol/inspector http://localhost:{port}/sse\n")

    from contoso_hr.mcp_server.server import mcp
    mcp.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
