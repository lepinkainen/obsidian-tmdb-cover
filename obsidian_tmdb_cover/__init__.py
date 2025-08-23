"""Obsidian TMDB Cover - Add TMDB cover images to Obsidian notes."""

__version__ = "0.1.0"
__author__ = "Your Name"

from .fetcher import TMDBCoverFetcher
from .updater import ObsidianNoteUpdater
from .utils import sanitize_filename, create_attachments_dir

__all__ = [
    "TMDBCoverFetcher",
    "ObsidianNoteUpdater",
    "sanitize_filename",
    "create_attachments_dir",
]
