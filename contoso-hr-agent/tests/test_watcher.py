"""
Unit tests for the resume watcher (no LLM calls, uses tmp_path).
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from contoso_hr.watcher.resume_watcher import WATCHED_EXTENSIONS, ResumeWatcher


class TestResumeWatcher:
    def test_watched_extensions(self):
        assert ".txt" in WATCHED_EXTENSIONS
        assert ".md" in WATCHED_EXTENSIONS
        assert ".pdf" in WATCHED_EXTENSIONS
        assert ".docx" in WATCHED_EXTENSIONS
        assert ".exe" not in WATCHED_EXTENSIONS
        assert ".pptx" not in WATCHED_EXTENSIONS  # pptx not a resume format

    def test_scan_existing_marks_files_as_seen(self, tmp_path):
        # Create some files in incoming/
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        (incoming / "existing.txt").write_text("existing resume")
        (incoming / "also_existing.md").write_text("another resume")

        config = MagicMock()
        config.incoming_dir = incoming
        config.processed_dir = tmp_path / "processed"
        config.outgoing_dir = tmp_path / "outgoing"
        config.watch_poll_seconds = 1

        watcher = ResumeWatcher(config)
        watcher._scan_existing()

        # Both existing files should be in _seen_files
        assert len(watcher._seen_files) == 2
        assert any("existing.txt" in f for f in watcher._seen_files)
        assert any("also_existing.md" in f for f in watcher._seen_files)

    def test_poll_detects_new_files(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()

        config = MagicMock()
        config.incoming_dir = incoming
        config.processed_dir = tmp_path / "processed"
        config.outgoing_dir = tmp_path / "outgoing"
        config.watch_poll_seconds = 1

        watcher = ResumeWatcher(config)
        processed_files = []

        with patch(
            "contoso_hr.watcher.resume_watcher.process_resume_file"
        ) as mock_process:
            mock_process.return_value = MagicMock(
                hr_decision=MagicMock(decision="advance", overall_score=80)
            )

            # Add a new file after watcher starts
            new_file = incoming / "new_resume.txt"
            new_file.write_text("Alice Zhang — Senior Cloud Engineer")

            watcher._poll()

            # Should have called process_resume_file once
            assert mock_process.call_count == 1
            assert mock_process.call_args[0][0] == new_file

    def test_poll_ignores_unsupported_extensions(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        (incoming / "resume.pptx").write_bytes(b"PK\x03\x04")  # PPTX not a resume format

        config = MagicMock()
        config.incoming_dir = incoming
        config.processed_dir = tmp_path / "processed"
        config.outgoing_dir = tmp_path / "outgoing"
        config.watch_poll_seconds = 1

        watcher = ResumeWatcher(config)

        with patch("contoso_hr.watcher.resume_watcher.process_resume_file") as mock_process:
            watcher._poll()
            mock_process.assert_not_called()  # .pptx is not in WATCHED_EXTENSIONS

    def test_poll_does_not_reprocess_seen_files(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        resume = incoming / "alice.txt"
        resume.write_text("Alice Zhang")

        config = MagicMock()
        config.incoming_dir = incoming
        config.processed_dir = tmp_path / "processed"
        config.outgoing_dir = tmp_path / "outgoing"
        config.watch_poll_seconds = 1

        watcher = ResumeWatcher(config)

        with patch("contoso_hr.watcher.resume_watcher.process_resume_file") as mock_process:
            mock_process.return_value = MagicMock(
                hr_decision=MagicMock(decision="advance", overall_score=80)
            )
            watcher._poll()   # first poll — should process
            assert mock_process.call_count == 1

            watcher._poll()   # second poll — already seen
            assert mock_process.call_count == 1  # still 1
