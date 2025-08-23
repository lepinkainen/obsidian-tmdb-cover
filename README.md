# Obsidian TMDB Cover

Add TMDB cover images and metadata to your Obsidian notes automatically.

## Features

- Fetches movie/TV show cover images from TheMovieDB (TMDB)
- Downloads and resizes images locally to your vault's `attachments/` folder
- Adds runtime and genre tags to note frontmatter
- Processes entire directories in batch mode
- Handles various cover scenarios (missing, color placeholders, external URLs)

## Installation

```bash
pip install obsidian-tmdb-cover
```

## Usage

**Bring Your Own API Key** - Get a free API key from [TheMovieDB](https://www.themoviedb.org/settings/api).

```bash
# Set your TMDB API key
export TMDB_API_KEY=your_api_key_here

# Process an Obsidian vault
obsidian-cover /path/to/your/obsidian/vault

# Or run as a module
python -m obsidian_tmdb_cover /path/to/your/obsidian/vault
```

The tool will:

1. Find all `.md` files in the directory
2. Extract titles from frontmatter, H1 headers, or filenames
3. Search TMDB for matching movies/TV shows
4. Download cover images and add metadata to frontmatter

## Example

Before:

```yaml
---
title: The Matrix
---
```

After:

```yaml
---
title: The Matrix
cover: attachments/The Matrix - cover.jpg
runtime: 136
tags: [movie/Action, movie/Science-Fiction]
---
```

## Requirements

- Python 3.8+
- TMDB API key (free)
- Obsidian vault with markdown files

## License

MIT
