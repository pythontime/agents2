"""
Structured logging setup with Rich formatting for Contoso HR Agent.

Provides clear, readable output for demos with role-based colors for
HR-domain agents: PolicyExpert, ResumeAnalyst, DecisionMaker.
"""

from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.theme import Theme


THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "role.policy": "bold magenta",
    "role.analyst": "bold blue",
    "role.decision": "bold yellow",
    "role.system": "bold white",
    "candidate": "bold cyan",
    "file": "dim",
})

console = Console(theme=THEME)


def setup_logging(level: str = "INFO", show_path: bool = False) -> logging.Logger:
    """Configure logging with Rich formatting."""
    from rich.logging import RichHandler
    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=show_path,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
    return logging.getLogger()


class HRLogger:
    """Structured logger for HR pipeline execution."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def start_run(self, run_id: str, candidate_id: str, filename: str):
        console.rule("[bold green]HR Evaluation Starting[/]")
        console.print(f"  [bold]Run ID:[/]     {run_id}")
        console.print(f"  [candidate]Candidate:[/] {candidate_id}")
        console.print(f"  [file]File:[/]      {filename}")
        console.print()

    def node_enter(self, node_name: str):
        style = self._get_role_style(node_name)
        self.logger.info(f"[{style}]▶ {node_name}[/]")

    def node_exit(self, node_name: str, summary: Optional[str] = None):
        style = self._get_role_style(node_name)
        msg = f"[{style}]✓ {node_name}[/]"
        if summary:
            msg += f" — {summary}"
        self.logger.info(msg)

    def agent_message(self, role: str, message: str):
        style = self._get_role_style(role)
        self.logger.info(f"  [{style}][{role.upper()}][/] {message}")

    def complete_run(
        self,
        run_id: str,
        candidate_id: str,
        decision: str,
        output_file: str,
        duration: Optional[float] = None,
    ):
        console.print()
        console.rule("[bold green]HR Evaluation Complete[/]")
        console.print(f"  [bold]Run ID:[/]    {run_id}")
        console.print(f"  [candidate]Candidate:[/] {candidate_id}")

        if decision == "advance":
            d = "[success]ADVANCE[/]"
        elif decision == "reject":
            d = "[error]REJECT[/]"
        else:
            d = "[warning]HOLD[/]"
        console.print(f"  [bold]Decision:[/] {d}")

        if duration is not None:
            console.print(f"  [bold]Duration:[/] {duration:.2f}s")
        console.print(f"  [file]Output:[/]   {output_file}")
        console.print()

    def error(self, message: str, exc: Optional[Exception] = None):
        self.logger.error(f"[error]✗ {message}[/]")
        if exc:
            self.logger.exception(exc)

    def warning(self, message: str):
        self.logger.warning(f"[warning]⚠ {message}[/]")

    def info(self, message: str):
        self.logger.info(message)

    def file_operation(self, operation: str, path: str):
        self.logger.info(f"  [file]{operation}:[/] {path}")

    def _get_role_style(self, name: str) -> str:
        name_lower = name.lower()
        if "policy" in name_lower:
            return "role.policy"
        elif "analyst" in name_lower or "resume" in name_lower:
            return "role.analyst"
        elif "decision" in name_lower or "decision_maker" in name_lower:
            return "role.decision"
        return "role.system"


_hr_logger: Optional[HRLogger] = None


def get_hr_logger() -> HRLogger:
    global _hr_logger
    if _hr_logger is None:
        _hr_logger = HRLogger()
    return _hr_logger


def print_banner():
    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║[/]  [bold white]Contoso HR Agent[/]                                        [bold cyan]║[/]")
    console.print("[bold cyan]║[/]  [dim]AI-Powered Resume Screening & HR Policy Q&A[/]            [bold cyan]║[/]")
    console.print("[bold cyan]╚══════════════════════════════════════════════════════════╝[/]")
    console.print()
