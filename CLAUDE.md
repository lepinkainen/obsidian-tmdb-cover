# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Go CLI tool that fetches movie/TV show cover images from TheMovieDB (TMDB) API and adds them to Obsidian markdown notes as frontmatter properties. It can also generate structured markdown content sections with TMDB data.

## Package Architecture

### Entry Point (`cmd/`)

- **`cmd/obsidian-tmdb-cover/main.go`** - CLI entry point with flag parsing
  - `--force` / `-f`: Force re-search even if TMDB ID is stored
  - `--generate-content` / `-g`: Generate TMDB content sections
  - `--content-sections`: Comma-separated list of sections (overview, info, seasons)

### Core Packages (`internal/`)

- **`internal/app/`** - Main application logic and orchestration
  - `Runner` struct coordinates processing flow
  - File discovery (single file or recursive directory scan)
  - Smart logic to determine what each note needs (cover, metadata, TMDB ID)
  - Integration with TUI selector for multiple search results
  - Content generation coordination

- **`internal/tmdb/`** - TMDB API client
  - Multi-search endpoint for movies/TV shows
  - Genre mapping with caching
  - Image download and resizing using `disintegration/imaging`
  - Metadata extraction (runtime, episodes, genres)
  - Full details fetching for content generation
  - Retry logic with exponential backoff
  - Support for custom HTTP clients (enables testing)

- **`internal/note/`** - Obsidian markdown note management
  - YAML frontmatter parsing with error handling
  - Title extraction priority: frontmatter → H1 header → filename
  - Relative path generation for cover images
  - Tag merging without duplicates
  - TMDB ID storage (`tmdb_id`, `tmdb_type` fields)
  - Content injection with `<!-- TMDB_DATA_START/END -->` markers
  - Smart detection of needs (cover, metadata, TMDB ID)

- **`internal/tui/`** - Bubble Tea TUI for selection
  - Interactive selector when multiple TMDB matches found
  - Styled cards with movie/TV info, ratings, overview
  - Actions: Select (Enter), Skip (s/Esc), Stop Processing (q/Ctrl+C)
  - Responsive layout with terminal size adaptation

- **`internal/content/`** - Markdown content generation
  - Builds structured markdown sections from TMDB data
  - Overview section with tagline
  - Info tables (status, runtime, ratings, links)
  - Seasons breakdown for TV shows
  - Country flags, streaming service links, IMDB/TVDB links
  - Content ratings and budget/revenue for movies

- **`internal/util/`** - Shared utilities
  - `SanitizeFilename()` - Cross-platform filename sanitization
  - `EnsureDir()` - Directory creation
  - `RelativeTo()` - Relative path calculation

## Development Commands

### Setup and Dependencies

```bash
# Install dependencies
go mod tidy

# Run tests
go test ./...

# Run tests with coverage
go test -cover ./...
```

### Building

```bash
# Build for current platform
go build -o bin/obsidian-tmdb-cover ./cmd/obsidian-tmdb-cover

# Build for multiple platforms
GOOS=linux GOARCH=amd64 go build -o bin/obsidian-tmdb-cover-linux ./cmd/obsidian-tmdb-cover
GOOS=darwin GOARCH=arm64 go build -o bin/obsidian-tmdb-cover-darwin ./cmd/obsidian-tmdb-cover
GOOS=windows GOARCH=amd64 go build -o bin/obsidian-tmdb-cover.exe ./cmd/obsidian-tmdb-cover
```

### Code Quality

```bash
# Format code
go fmt ./...
gofmt -s -w .

# Static analysis
go vet ./...

# Run linter (if golangci-lint is installed)
golangci-lint run
```

### Running the Tool

```bash
# Set TMDB API key (required)
export TMDB_API_KEY=your_api_key_here

# Process a vault
./bin/obsidian-tmdb-cover /path/to/obsidian/vault

# Process a single file
./bin/obsidian-tmdb-cover /path/to/note.md

# Force re-search even with stored IDs
./bin/obsidian-tmdb-cover --force /path/to/vault

# Generate content sections
./bin/obsidian-tmdb-cover --generate-content /path/to/vault

# Custom content sections
./bin/obsidian-tmdb-cover --generate-content --content-sections overview,info /path/to/vault
```

### Testing

```bash
# Run all tests
go test ./...

# Run specific package tests
go test ./internal/note
go test ./internal/tmdb

# Run tests with verbose output
go test -v ./...

# Run tests with race detector
go test -race ./...
```

## Key Implementation Patterns

### Smart Processing Logic

The app determines what each note needs before fetching from TMDB:

```go
needsCover := n.NeedsCover()      // No cover, HTML color, or external URL
needsMetadata := n.NeedsMetadata() // Missing runtime or genre tags
needsTMDB := n.NeedsTMDB()         // Missing TMDB ID or type
```

If a note already has a TMDB ID stored, it uses direct lookup instead of searching (unless `--force` is used).

### TUI Selection

When multiple TMDB results are found, the TUI presents an interactive selector:

- Shows styled cards with title, year, type, rating, and overview
- User can navigate with arrow keys, select with Enter
- Skip individual notes with 's' or Esc
- Stop all processing with 'q' or Ctrl+C

### Content Generation

Content sections are generated from full TMDB details and injected between markers:

```markdown
<!-- TMDB_DATA_START -->
## Overview
...
## Movie Info
...
<!-- TMDB_DATA_END -->
```

This allows content to be regenerated without losing custom notes above/below.

### YAML Frontmatter Handling

Robust frontmatter parsing with fallback for malformed YAML:

```go
if err := yaml.Unmarshal([]byte(fm), &n.frontmatter); err != nil {
    n.frontmatter = make(map[string]any)
    n.body = content  // Treat entire file as body
}
```

### Genre Tag Sanitization

Converts TMDB genre names to valid Obsidian tags:

- `"Sci-Fi & Fantasy"` → `"tv/Sci-Fi-and-Fantasy"`
- `"Science Fiction"` → `"movie/Science-Fiction"`
- Removes `#` symbols, replaces `/` with `-`, converts spaces to `-`

### TMDB ID Storage

Notes store TMDB identifiers in frontmatter for future lookups:

```yaml
tmdb_id: 603       # The Matrix
tmdb_type: movie   # or "tv"
```

## Testing Strategy

Go tests cover:

- **TMDB client**: Search, metadata fetching, genre mapping (with mocked HTTP) in `internal/tmdb/client_internal_test.go`
- **Note parsing**: Frontmatter parsing, title extraction, needs detection in `internal/note/note_test.go`
- **File utilities**: Filename sanitization, path operations

Test structure follows Go conventions: `*_test.go` files alongside code, table-driven tests where appropriate.

## Dependencies

- **github.com/charmbracelet/bubbletea** - TUI framework
- **github.com/charmbracelet/lipgloss** - Terminal styling
- **github.com/charmbracelet/bubbles** - TUI components (list)
- **github.com/disintegration/imaging** - Image processing and resizing
- **gopkg.in/yaml.v3** - YAML parsing
