"""
LangGraph checkpoint management for Contoso HR Agent.

SqliteSaver persists the full LangGraph state to checkpoints.db,
enabling cross-run memory per session_id (used as thread_id).
"""

from __future__ import annotations

from pathlib import Path


def get_checkpointer(data_dir: Path):
    """Return a SqliteSaver instance for LangGraph checkpointing.

    The checkpointer DB is separate from the app SQLite store (hr.db)
    to keep LangGraph internals isolated.

    Args:
        data_dir: Directory where checkpoints.db will be created.

    Returns:
        langgraph.checkpoint.sqlite.SqliteSaver instance.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    data_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_db = data_dir / "checkpoints.db"
    return SqliteSaver.from_conn_string(str(checkpoint_db))


def make_thread_config(session_id: str) -> dict:
    """Return the LangGraph run config for a given session.

    Using a stable session_id as thread_id means the graph resumes
    from the last checkpoint for that candidate/session on repeated invocations.

    Args:
        session_id: Unique identifier for this evaluation session.

    Returns:
        LangGraph config dict with thread_id set.
    """
    return {"configurable": {"thread_id": session_id}}
