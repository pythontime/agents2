"""
Port management utilities.

Ensures clean startup by killing any processes occupying the target port
before binding. Cross-platform: Windows (netstat/taskkill) and Unix (fuser/lsof).
"""

from __future__ import annotations

import subprocess
import sys
import time
from rich.console import Console

console = Console()


def force_kill_port(port: int) -> None:
    """Kill all processes listening on the given port.

    Called at startup of engine.py and mcp_server/__main__.py to guarantee
    the port is free before binding. Silently succeeds if nothing is listening.

    Args:
        port: TCP port number to free up.
    """
    console.print(f"[dim]Checking port {port}...[/]")

    if sys.platform == "win32":
        _kill_port_windows(port)
    else:
        _kill_port_unix(port)

    time.sleep(0.5)  # brief settle after kill


def _kill_port_windows(port: int) -> None:
    """Windows implementation: netstat + taskkill."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        pids_killed: set[str] = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid not in pids_killed and pid != "0":
                        pids_killed.add(pid)
                        subprocess.run(
                            ["taskkill", "/PID", pid, "/F"],
                            capture_output=True,
                            timeout=5,
                        )
                        console.print(f"[dim]  Killed PID {pid} on port {port}[/]")
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass


def _kill_port_unix(port: int) -> None:
    """Unix implementation: fuser (Linux) or lsof (macOS)."""
    # Try fuser first (Linux)
    try:
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            console.print(f"[dim]  Killed process on port {port} via fuser[/]")
        return
    except FileNotFoundError:
        pass

    # Fallback: lsof + kill (macOS)
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            for pid in result.stdout.strip().splitlines():
                subprocess.run(["kill", "-9", pid], capture_output=True, timeout=5)
                console.print(f"[dim]  Killed PID {pid} on port {port} via lsof[/]")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass


def wait_for_port_free(port: int, timeout_seconds: float = 5.0) -> bool:
    """Wait until a port is no longer in use.

    Args:
        port: Port to wait on.
        timeout_seconds: Maximum wait time.

    Returns:
        True if port is free within timeout, False otherwise.
    """
    import socket

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                time.sleep(0.2)
        except (ConnectionRefusedError, OSError):
            return True
    return False
