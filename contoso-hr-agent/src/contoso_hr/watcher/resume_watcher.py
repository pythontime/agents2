"""
Resume Watcher — polls data/incoming/ for new resume files.

When a new .txt or .md file appears, it automatically runs the full
HR evaluation pipeline and saves the result. Files are archived to
data/processed/ after processing to prevent reprocessing.

Usage:
    uv run hr-watcher
    uv run hr-watcher --poll-interval 5
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from ..config import Config, get_config
from ..logging_setup import get_hr_logger, print_banner, setup_logging
from ..util.fs import ensure_dirs
from .process_resume import process_resume_file

WATCHED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class ResumeWatcher:
    """Poll data/incoming/ for new resume files and trigger evaluation.

    Uses a _seen_files sentinel set (same pattern as oreilly-agent-mvp FolderWatcher)
    to avoid reprocessing files that existed before the watcher started.
    """

    def __init__(self, config: Config, poll_interval: Optional[float] = None):
        """Initialize the watcher.

        Args:
            config: Application config.
            poll_interval: Override poll interval (defaults to config.watch_poll_seconds).
        """
        self.config = config
        self.poll_interval = poll_interval or config.watch_poll_seconds
        self._seen_files: set[str] = set()
        self._running = False

    def start(self) -> None:
        """Start the polling loop. Blocks until stopped (Ctrl+C or SIGTERM)."""
        logger = get_hr_logger()

        ensure_dirs(
            self.config.incoming_dir,
            self.config.processed_dir,
            self.config.outgoing_dir,
        )

        # Mark pre-existing files as seen (don't re-process on startup)
        self._scan_existing()

        self._running = True

        # Graceful shutdown on SIGTERM
        def _handle_sigterm(signum, frame):
            logger.info("SIGTERM received — shutting down watcher...")
            self._running = False

        signal.signal(signal.SIGTERM, _handle_sigterm)

        logger.info(
            f"[bold cyan]Watching {self.config.incoming_dir} "
            f"(every {self.poll_interval}s)[/]"
        )
        logger.info("Drop a .txt or .md resume file into the folder to trigger evaluation.")

        try:
            while self._running:
                self._poll()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt — watcher stopped.")

    def _scan_existing(self) -> None:
        """Mark all files currently in incoming/ as already-seen."""
        for fp in self.config.incoming_dir.iterdir():
            if fp.suffix.lower() in WATCHED_EXTENSIONS:
                self._seen_files.add(str(fp.resolve()))

    def _poll(self) -> None:
        """Check for new files and process them."""
        logger = get_hr_logger()
        try:
            current = [
                fp for fp in self.config.incoming_dir.iterdir()
                if fp.suffix.lower() in WATCHED_EXTENSIONS
            ]
        except Exception as e:
            logger.warning(f"Poll error: {e}")
            return

        for fp in current:
            key = str(fp.resolve())
            if key not in self._seen_files:
                self._seen_files.add(key)
                if fp.exists():  # may have been moved between poll and processing
                    logger.info(f"[bold cyan]New resume detected: {fp.name}[/]")
                    try:
                        result = process_resume_file(fp, self.config)
                        if result:
                            logger.info(
                                f"[bold green]✓ {fp.name} → "
                                f"{result.hr_decision.decision.upper()} "
                                f"(score: {result.hr_decision.overall_score})[/]"
                            )
                        else:
                            logger.warning(f"Processing returned no result for {fp.name}")
                    except Exception as e:
                        logger.error(f"Failed to process {fp.name}: {e}", e)


def main() -> None:
    """CLI entry point for the resume watcher."""
    parser = argparse.ArgumentParser(description="Contoso HR Resume Watcher")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between folder polls (default: from .env WATCH_POLL_SECONDS)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
    )
    args = parser.parse_args()

    config = get_config()
    setup_logging(args.log_level or config.log_level)
    print_banner()

    watcher = ResumeWatcher(config, poll_interval=args.poll_interval)
    watcher.start()
    sys.exit(0)
