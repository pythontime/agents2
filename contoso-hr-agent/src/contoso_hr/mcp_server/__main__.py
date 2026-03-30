"""
Contoso HR Agent MCP Server entry point.

Default:  SSE transport on MCP_PORT (8081).
Stdio:    pass --stdio flag — used by MCP Inspector for local dev.

Connect MCP Inspector (stdio):
  npx @modelcontextprotocol/inspector uv run hr-mcp --stdio
"""

from __future__ import annotations
import sys


def main() -> None:
    """Start FastMCP 2 — stdio if --stdio flag present, else SSE on MCP_PORT."""
    stdio_mode = "--stdio" in sys.argv

    from contoso_hr.config import get_config
    from contoso_hr.logging_setup import console, setup_logging

    config = get_config()
    setup_logging(config.log_level)

    from contoso_hr.mcp_server.server import mcp

    if stdio_mode:
        mcp.run(transport="stdio")
    else:
        from contoso_hr.util.port_utils import force_kill_port
        port = config.mcp_port
        force_kill_port(port)
        console.print(f"\n[bold cyan]Contoso HR MCP Server[/]")
        console.print(f"  SSE endpoint: [link]http://localhost:{port}/sse[/]")
        console.print(f"  MCP Inspector (stdio): npx @modelcontextprotocol/inspector uv run hr-mcp --stdio\n")
        mcp.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
