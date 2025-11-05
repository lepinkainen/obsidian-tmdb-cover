# Repository Guidelines

## Project Structure & Module Organization
- `cmd/obsidian-tmdb-cover` hosts the CLI entry; `internal/app` orchestrates vault traversal while `internal/{note,tmdb,content,tui,util}` handle markdown, API, rendering, and helpers.
- Keep transient binaries in `bin/` (gitignored) and anonymised fixtures in `testdata/`; update `llm-shared/` only when syncing shared tooling.

## Shared Tooling & References
- Review `llm-shared/project_tech_stack.md` and `llm-shared/languages/go.md` for branch flow, dependency policy, and the `goimports` requirement.
- Use modern shell helpers (`rg`, `fd`) per `llm-shared/shell_commands.md`.
- When altering structure, run `go run llm-shared/utils/validate-docs.go --dir .` to confirm layout and required files.

## Build, Test, and Development Commands
- `task lint` runs the goimports format check plus `go vet` and `golangci-lint`.
- `task test` runs the standard suite; `task test-ci` adds `-tags=ci` and writes `coverage.out`.
- `task build` compiles after lint/test locally; `task build-ci` is the compile-only step used in automation.
- `task fmt` applies goimports formatting; `task clean` clears `build/` and coverage artifacts.
- `go run ./cmd/obsidian-tmdb-cover --help` remains useful for quick local validation.

## Coding Style & Naming Conventions
- Use the Go version from `llm-shared/versions.md`; format via `goimports -w .` (avoid raw `gofmt`).
- Exported identifiers use PascalCase, internal helpers use camelCase, and files stay snake_case with `_test.go` reserved for tests.
- Avoid mutable package-level state and preserve indentation in generated markdown blocks to minimise diffs.

## Testing Guidelines
- Co-locate table-driven tests with code under `internal/**`; follow `internal/tmdb/client_internal_test.go` for HTTP client stubs.
- Run `go test ./...` locally (add `-race` or targeted packages as needed) and call out any unavoidable coverage gaps in PR notes.

## Commit & Pull Request Guidelines
- Follow the conventional commit prefixes (`feat:`, `fix:`, `chore:`) with imperative subjects.
- Keep PRs focused, summarise user impact, list executed checks (`task lint`, `task test-ci`, `task build-ci`), and attach UX screenshots for TUI changes.

## CI & Automation
- `.github/workflows/ci.yml` runs `task lint`, `task test-ci`, and `task build-ci` on pushes to `main`/`develop`, PRs into `main`, and a nightly cron.
- Reproduce failures locally with the matching Task commands; ensure `goimports` and `golangci-lint` are installed (`go install ...@latest`) before running CI-linked tasks.
- Coverage reports output to `coverage.out` for artifact uploads or external services.

## Security & Configuration Tips
- Source `TMDB_API_KEY` through environment variables or `.envrc`; never commit secrets or personal vault data.
- Scrub TMDB payloads and file paths from diagnostic logs before sharing outside the team.
