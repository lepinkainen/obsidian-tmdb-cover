"""Obsidian TMDB Cover - Add TMDB cover images to Obsidian notes."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("obsidian-tmdb-cover")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development

__author__ = "Riku Lindblad"

from .fetcher import TMDBCoverFetcher
from .updater import ObsidianNoteUpdater
from .utils import sanitize_filename, create_attachments_dir

__all__ = [
    "TMDBCoverFetcher",
    "ObsidianNoteUpdater",
    "sanitize_filename",
    "create_attachments_dir",
]
