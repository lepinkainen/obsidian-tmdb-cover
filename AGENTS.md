# Repository Guidelines

## Project Structure & Module Organization
- `obsidian_tmdb_cover/`: core package; `cli.py` drives the CLI entry point, `__main__.py` enables `python -m`, `fetcher.py` wraps TMDB API calls, `content_builder.py` prepares frontmatter, `tui.py` presents selection UI, `updater.py` writes note updates, and `utils.py` hosts shared helpers.
- `tests/`: pytest suite exercising metadata generation (`test_metadata.py`).
- `attachments/` holds example output assets; `dist/` stores build artifacts; `Taskfile.yml` defines repeatable automation; `fetch_tv_details.py` is a helper script for bulk TMDB lookups.

## Build, Test, and Development Commands
- `uv sync`: install project and dev dependencies from `pyproject.toml`.
- `task build` (or `task build-python`): build wheel/sdist into `dist/`.
- `task test` (or `uv run pytest tests/`): execute the unit test suite.
- `task lint`: run Ruff lint/format plus MyPy type checks.
- `uv run obsidian-tmdb-cover /path/to/vault`: run the CLI; export `TMDB_API_KEY` first.

## Coding Style & Naming Conventions
- Target Python 3.8+ with 4-space indentation and type hints on public functions.
- Keep modules focused; prefer pure helpers in `utils.py` and side-effect code in `updater.py` or `cli.py`.
- Run `uv run ruff check .` and `uv run ruff format .` before pushing; honor Ruff fixes.
- Use snake_case for functions/variables, PascalCase for classes, and update docstrings when behavior shifts.

## Testing Guidelines
- Place tests under `tests/`, mirroring module names (e.g., metadata logic lives in `test_metadata.py`).
- Use pytest fixtures and mocks to avoid network calls or vault writes.
- For coverage, run `uv run pytest tests/ --cov=obsidian_tmdb_cover`; keep new code covered.
- Name tests `test_<scenario>_<expectation>` so failures point to intent.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `chore:`); keep the subject under 72 characters and in present tense.
- Separate functional and refactor changes; describe rationale in the body when touching CLI/TUI flows.
- PRs should summarize impact, list verification commands, link issues, and add screenshots or terminal captures when UX changes.

## Configuration & Secrets
- Export `TMDB_API_KEY` in your shell or `.env`; never commit real keys or vault paths.
- Document any new config flags or environment variables in `README.md` and note defaults in code comments where they are read.
