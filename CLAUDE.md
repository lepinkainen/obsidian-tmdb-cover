# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that fetches movie/TV show cover images from TheMovieDB (TMDB) API and adds them to Obsidian markdown notes as frontmatter properties. The script processes entire directories in batch mode only.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies (using uv)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Code Quality
```bash
# Format and lint code
uv run ruff format .
uv run ruff check .

# Type checking
uv run mypy obsidian-cover.py
```

### Running the Script
```bash
# Set TMDB API key (required)
export TMDB_API_KEY=your_api_key_here

# Run the script with a directory path
python obsidian-cover.py /path/to/obsidian/vault

# Or run interactively
python obsidian-cover.py
```

## Architecture

The codebase consists of two main classes:

### TMDBCoverFetcher (obsidian-cover.py:16-61)
- Handles TMDB API interactions
- Searches for movies/TV shows using multi-search endpoint
- Returns poster image URLs from TMDB

### ObsidianNoteUpdater (obsidian-cover.py:63-144)  
- Parses Obsidian markdown files with YAML frontmatter
- Extracts titles from frontmatter, H1 headers, or filenames
- Updates frontmatter with cover URLs and saves files

The main execution flow processes all markdown files in a specified directory, with options to process all files or select specific ones.

## Key Implementation Details

- Uses YAML frontmatter parsing to extract and update note metadata
- Prioritizes title extraction: frontmatter > H1 heading > filename
- Safely handles malformed YAML frontmatter
- Preserves file encoding (UTF-8) when reading/writing files
- API responses are filtered to only include results with poster images