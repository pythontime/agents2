"""
File system utilities for safe file operations.

All operations use pathlib for Windows compatibility.
Implements atomic moves to prevent data loss during resume processing.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Union


def ensure_dirs(*dirs: Union[str, Path]) -> None:
    """Ensure directories exist, creating them if needed."""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def atomic_move(src: Union[str, Path], dest: Union[str, Path]) -> Path:
    """Atomically move a file from src to dest.

    Args:
        src: Source file path.
        dest: Destination file path.

    Returns:
        The destination path.
    """
    src = Path(src)
    dest = Path(dest)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


def get_timestamped_filename(prefix: str, extension: str = ".json") -> str:
    """Generate a timestamped filename like 'prefix_20240115_143022.json'."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not extension.startswith("."):
        extension = "." + extension
    return f"{prefix}_{timestamp}{extension}"


def safe_write_json(content: str, path: Union[str, Path]) -> Path:
    """Write JSON content atomically (temp file → move to final)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    shutil.move(str(temp_path), str(path))
    return path


def list_text_files(directory: Union[str, Path]) -> list[Path]:
    """List all supported knowledge document files in a directory, sorted by name."""
    directory = Path(directory)
    if not directory.exists():
        return []
    files = []
    for ext in ("*.txt", "*.md", "*.pdf", "*.doc", "*.docx", "*.pptx"):
        files.extend(directory.glob(ext))
    return sorted(files)


def list_resume_files(directory: Union[str, Path]) -> list[Path]:
    """List all supported resume files (.txt, .md, .pdf, .docx) in a directory."""
    directory = Path(directory)
    if not directory.exists():
        return []
    files = []
    for ext in ("*.txt", "*.md", "*.pdf", "*.docx"):
        files.extend(directory.glob(ext))
    return sorted(files)
