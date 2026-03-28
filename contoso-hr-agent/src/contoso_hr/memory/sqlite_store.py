"""
SQLite persistence store for Contoso HR Agent.

Stores candidate evaluations in hr.db with:
  - candidates: lightweight metadata for fast queries and the web grid
  - evaluations: full EvaluationResult JSON
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from ..models import CandidateSummary, EvaluationResult


class HRSQLiteStore:
    """Persist and query HR evaluation results.

    Uses a connection-per-call pattern for thread safety.
    """

    def __init__(self, db_path: Path):
        """Initialize the store and ensure schema exists.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id    TEXT PRIMARY KEY,
                    run_id          TEXT NOT NULL,
                    filename        TEXT NOT NULL,
                    candidate_name  TEXT,
                    decision        TEXT,
                    overall_score   INTEGER,
                    skills_score    INTEGER,
                    experience_score INTEGER,
                    source          TEXT,
                    started_at      TEXT,
                    completed_at    TEXT,
                    duration_seconds REAL
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    candidate_id    TEXT PRIMARY KEY,
                    run_id          TEXT NOT NULL,
                    result_json     TEXT NOT NULL,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
                );

                CREATE INDEX IF NOT EXISTS idx_candidates_decision
                    ON candidates(decision);
                CREATE INDEX IF NOT EXISTS idx_candidates_completed
                    ON candidates(completed_at);
                CREATE INDEX IF NOT EXISTS idx_candidates_score
                    ON candidates(overall_score DESC);
            """)

    def save_result(self, result: EvaluationResult) -> None:
        """Persist a full EvaluationResult to SQLite.

        Upserts both the candidates metadata row and the full JSON.

        Args:
            result: Completed EvaluationResult from the pipeline.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO candidates
                    (candidate_id, run_id, filename, candidate_name, decision,
                     overall_score, skills_score, experience_score, source,
                     completed_at, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.candidate_id,
                    result.run_id,
                    result.filename,
                    result.candidate_name,
                    result.hr_decision.decision,
                    result.hr_decision.overall_score,
                    result.candidate_eval.skills_match_score,
                    result.candidate_eval.experience_score,
                    getattr(result.candidate_eval, "source", "unknown"),
                    result.timestamp_utc,
                    result.duration_seconds,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO evaluations (candidate_id, run_id, result_json)
                VALUES (?, ?, ?)
                """,
                (result.candidate_id, result.run_id, result.model_dump_json()),
            )

    def get_result(self, candidate_id: str) -> Optional[EvaluationResult]:
        """Load a full EvaluationResult by candidate_id.

        Args:
            candidate_id: Unique candidate identifier.

        Returns:
            Deserialized EvaluationResult or None if not found.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT result_json FROM evaluations WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        if not row:
            return None
        return EvaluationResult.model_validate_json(row["result_json"])

    def get_recent_candidates(self, limit: int = 20) -> list[CandidateSummary]:
        """Return recent candidate summaries ordered by completion time.

        Args:
            limit: Maximum number of results.

        Returns:
            List of CandidateSummary objects for the web grid.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT candidate_id, run_id, filename, candidate_name,
                       decision, overall_score, completed_at, duration_seconds
                FROM candidates
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            CandidateSummary(
                candidate_id=r["candidate_id"],
                run_id=r["run_id"],
                filename=r["filename"],
                candidate_name=r["candidate_name"] or "Unknown",
                decision=r["decision"] or "unknown",
                overall_score=r["overall_score"] or 0,
                timestamp_utc=r["completed_at"] or "",
                duration_seconds=r["duration_seconds"],
            )
            for r in rows
        ]

    def get_candidates_by_decision(
        self, decision: str, limit: int = 50
    ) -> list[CandidateSummary]:
        """Filter candidates by decision (advance/hold/reject).

        Args:
            decision: Decision value to filter by.
            limit: Maximum results.

        Returns:
            Filtered list of CandidateSummary objects.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT candidate_id, run_id, filename, candidate_name,
                       decision, overall_score, completed_at, duration_seconds
                FROM candidates WHERE decision = ?
                ORDER BY completed_at DESC LIMIT ?
                """,
                (decision, limit),
            ).fetchall()
        return [
            CandidateSummary(
                candidate_id=r["candidate_id"],
                run_id=r["run_id"],
                filename=r["filename"],
                candidate_name=r["candidate_name"] or "Unknown",
                decision=r["decision"],
                overall_score=r["overall_score"] or 0,
                timestamp_utc=r["completed_at"] or "",
                duration_seconds=r["duration_seconds"],
            )
            for r in rows
        ]

    def get_stats(self) -> dict:
        """Return aggregate statistics for the candidates dashboard.

        Returns:
            Dict with total counts, decision breakdown, and average score.
        """
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            by_decision = {
                r["decision"]: r["cnt"]
                for r in conn.execute(
                    "SELECT decision, COUNT(*) as cnt FROM candidates GROUP BY decision"
                ).fetchall()
            }
            avg_score = conn.execute(
                "SELECT AVG(overall_score) FROM candidates WHERE overall_score IS NOT NULL"
            ).fetchone()[0]
            avg_duration = conn.execute(
                "SELECT AVG(duration_seconds) FROM candidates WHERE duration_seconds IS NOT NULL"
            ).fetchone()[0]

        return {
            "total_evaluations": total,
            "by_decision": by_decision,
            "average_score": round(avg_score or 0, 1),
            "average_duration_seconds": round(avg_duration or 0, 1),
        }
