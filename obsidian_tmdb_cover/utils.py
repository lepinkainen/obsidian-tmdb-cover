"""Utility functions for obsidian-tmdb-cover package."""

from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Limit length
    if len(filename) > 200:
        filename = filename[:200]

    return filename


def create_attachments_dir(base_dir: Path) -> Path:
    """Create and return the attachments directory path"""
    attachments_dir = base_dir / "attachments"
    attachments_dir.mkdir(exist_ok=True)
    return attachments_dir
