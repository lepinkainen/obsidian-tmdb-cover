# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PyPI-ready Python package that fetches movie/TV show cover images from TheMovieDB (TMDB) API and adds them to Obsidian markdown notes as frontmatter properties. The package has been refactored from a monolithic script into a proper Python package structure for distribution.

## Package Architecture

### Core Components (`obsidian_tmdb_cover/`)

- **`fetcher.py`** - `TMDBCoverFetcher` class handles all TMDB API interactions
  - Multi-search endpoint for movies/TV shows
  - Genre mapping with caching (`_genre_cache`)
  - Image download and resizing (PIL/Pillow)
  - Metadata extraction (runtime, genres)

- **`updater.py`** - `ObsidianNoteUpdater` class manages Obsidian markdown files
  - YAML frontmatter parsing with error handling
  - Title extraction priority: frontmatter → H1 header → filename
  - Relative path generation for cover images
  - Tag merging and metadata updates

- **`utils.py`** - Shared utility functions
  - `sanitize_filename()` - Cross-platform filename sanitization
  - `create_attachments_dir()` - Creates `attachments/` directory

- **`cli.py`** - Command-line interface and main processing logic
  - Batch processing of markdown files
  - Smart logic for cover/metadata needs detection
  - Progress reporting and error handling

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies (using uv)
uv sync

# Install package in development mode
uv run python -m pip install -e .
```

### Code Quality (follows llm-shared guidelines)
```bash
# Format and lint code
uv run ruff format .
uv run ruff check .

# Type checking (handles PIL import issues automatically)
uv run mypy obsidian_tmdb_cover/
```

### Running the Package
```bash
# Set TMDB API key (required)
export TMDB_API_KEY=your_api_key_here

# Via console script
uv run obsidian-cover /path/to/obsidian/vault

# Via module execution
uv run python -m obsidian_tmdb_cover /path/to/obsidian/vault
```

### Testing
```bash
# Run basic functionality tests (requires TMDB_API_KEY for full tests)
uv run python test_metadata.py
```

## Key Implementation Patterns

### Smart Processing Logic
The CLI implements intelligent processing that checks what each note needs:
```python
# Determines if cover is needed (no cover, color placeholder, or external URL)
needs_cover = (
    not existing_cover
    or note._is_html_color_code(existing_cover)
    or note.has_external_cover()
)

# Determines if metadata is needed (missing runtime or genre tags)
needs_metadata = not existing_runtime or not has_genre_tags
```

### YAML Frontmatter Handling
Robust frontmatter parsing with fallback for malformed YAML:
```python
try:
    self.frontmatter = yaml.safe_load(frontmatter_str) or {}
except yaml.YAMLError:
    self.frontmatter = {}  # Graceful fallback
```

### Genre Tag Sanitization
Converts TMDB genre names to valid Obsidian tags:
- `"Sci-Fi & Fantasy"` → `"movie/Sci-Fi-and-Fantasy"`
- Removes `#` symbols, replaces `/` and spaces with `-`

### PyPI Package Structure
- Entry points: `obsidian-cover = "obsidian_tmdb_cover.cli:main"`
- Module execution: `__main__.py` enables `python -m obsidian_tmdb_cover`
- Proper imports with `__all__` declarations in `__init__.py`

## Testing Strategy

Basic unit tests in `test_metadata.py` cover:
- Frontmatter parsing and updates
- Tag merging without duplicates
- Genre name sanitization
- TMDB API integration (with API key)

Test structure follows the pattern: temporary file creation → operation → verification → cleanup.