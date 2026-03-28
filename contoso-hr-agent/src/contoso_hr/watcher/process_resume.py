"""
Resume processing orchestration.

Called by the file watcher and by the web API upload endpoint.
Validates the resume, runs the HR evaluation pipeline,
persists the result, and writes the output JSON.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ..config import get_config
from ..logging_setup import get_hr_logger
from ..memory.checkpoints import make_thread_config
from ..memory.sqlite_store import HRSQLiteStore
from ..models import EvaluationResult, ResumeSubmission
from ..pipeline.graph import create_hr_graph
from ..util.fs import atomic_move, ensure_dirs, get_timestamped_filename, safe_write_json


def process_resume_file(
    file_path: Path,
    config=None,
) -> Optional[EvaluationResult]:
    """Process a resume file through the full HR evaluation pipeline.

    Steps:
    1. Read and validate the file as plain text
    2. Move to data/processed/
    3. Run the LangGraph pipeline
    4. Save result JSON to data/outgoing/
    5. Persist to SQLite

    Args:
        file_path: Path to the resume file (.txt or .md).
        config: Config instance. Uses global config if None.

    Returns:
        EvaluationResult on success, None on failure.
    """
    logger = get_hr_logger()
    if config is None:
        config = get_config()

    ensure_dirs(
        config.incoming_dir,
        config.processed_dir,
        config.outgoing_dir,
        config.data_dir,
    )

    # Extract text (handles .txt, .md, .pdf, .docx)
    try:
        from ..knowledge.vectorizer import extract_text
        raw_text = extract_text(file_path).strip()
        if not raw_text:
            logger.warning(f"No extractable text in: {file_path.name}")
            return None
    except Exception as e:
        logger.error(f"Cannot extract text from {file_path.name}: {e}")
        return None

    return process_resume_text(raw_text, file_path.name, config, source_path=file_path)


def process_resume_text(
    raw_text: str,
    filename: str,
    config=None,
    source_path: Optional[Path] = None,
) -> Optional[EvaluationResult]:
    """Process resume text directly (used by web API upload).

    Args:
        raw_text: Resume content as plain text.
        filename: Original filename (used for display and ID generation).
        config: Config instance. Uses global config if None.
        source_path: If set, move this file to processed/ after evaluation.

    Returns:
        EvaluationResult on success, None on failure.
    """
    logger = get_hr_logger()
    if config is None:
        config = get_config()

    ensure_dirs(config.processed_dir, config.outgoing_dir, config.data_dir)

    # Move source file to processed/ (if applicable)
    if source_path and source_path.exists():
        dest = config.processed_dir / get_timestamped_filename(source_path.stem, source_path.suffix)
        try:
            atomic_move(source_path, dest)
            logger.file_operation("Archived", str(dest))
        except Exception as e:
            logger.warning(f"Could not archive {source_path.name}: {e}")

    # Build the submission
    submission = ResumeSubmission(
        filename=filename,
        raw_text=raw_text,
        source="upload" if source_path is None else "incoming_folder",
    )

    run_id = str(uuid4())
    start_time = time.time()

    logger.start_run(run_id, submission.candidate_id, filename)

    initial_state = {
        "session_id": submission.session_id,
        "run_id": run_id,
        "start_time": start_time,
        "resume": submission.model_dump(),
    }

    # Run the LangGraph pipeline with SqliteSaver checkpointing
    try:
        graph = create_hr_graph(config.data_dir)
        thread_config = make_thread_config(submission.session_id)
        final_state = graph.invoke(initial_state, config=thread_config)
    except Exception as e:
        logger.error(f"Pipeline invocation failed: {e}", e)
        return None

    result_data = final_state.get("result")
    if not result_data:
        logger.error("Pipeline returned no result")
        return None

    try:
        result = EvaluationResult(**result_data)
    except Exception as e:
        logger.error(f"Could not parse pipeline result: {e}", e)
        return None

    # Write JSON output
    output_filename = get_timestamped_filename(submission.candidate_id)
    output_path = config.outgoing_dir / output_filename
    try:
        safe_write_json(result.model_dump_json(indent=2), output_path)
        logger.file_operation("Wrote result", str(output_path))
    except Exception as e:
        logger.warning(f"Could not write output JSON: {e}")

    # Persist to SQLite
    try:
        store = HRSQLiteStore(config.data_dir / "hr.db")
        store.save_result(result)
        logger.file_operation("Persisted", str(config.data_dir / "hr.db"))
    except Exception as e:
        logger.warning(f"SQLite persist failed: {e}")

    return result
