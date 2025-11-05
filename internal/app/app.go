// Package app provides the main application logic for obsidian-tmdb-cover.
package app

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/lepinkainen/obsidian-tmdb-cover/internal/content"
	"github.com/lepinkainen/obsidian-tmdb-cover/internal/note"
	"github.com/lepinkainen/obsidian-tmdb-cover/internal/tmdb"
	"github.com/lepinkainen/obsidian-tmdb-cover/internal/tui"
	"github.com/lepinkainen/obsidian-tmdb-cover/internal/util"
)

// ErrStopProcessing is returned when the user requests to stop processing via the TUI.
var ErrStopProcessing = errors.New("processing stopped by user")

// Config holds the application configuration.
type Config struct {
	Path            string
	Force           bool
	GenerateContent bool
	ContentSections []string
}

// Runner coordinates the note processing workflow.
type Runner struct {
	client *tmdb.Client
	cfg    Config
}

// NewRunner creates a new Runner with the given TMDB client and configuration.
func NewRunner(client *tmdb.Client, cfg Config) *Runner {
	return &Runner{
		client: client,
		cfg:    cfg,
	}
}

// Run executes the main application logic.
func (r *Runner) Run(ctx context.Context) error {
	info, err := os.Stat(r.cfg.Path)
	if err != nil {
		return err
	}

	var files []string
	var vaultPath string

	if info.IsDir() {
		vaultPath = r.cfg.Path
		err = filepath.WalkDir(r.cfg.Path, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.IsDir() {
				return nil
			}
			if strings.EqualFold(filepath.Ext(path), ".md") {
				files = append(files, path)
			}
			return nil
		})
		if err != nil {
			return err
		}
		fmt.Printf("Found %d markdown files\n", len(files))
		if len(files) == 0 {
			return errors.New("no markdown files found in the directory")
		}
	} else {
		if !strings.EqualFold(filepath.Ext(r.cfg.Path), ".md") {
			return fmt.Errorf("file is not a markdown file: %s", r.cfg.Path)
		}
		files = []string{r.cfg.Path}
		vaultPath = filepath.Dir(r.cfg.Path)
		fmt.Printf("Processing single file: %s\n", filepath.Base(r.cfg.Path))
	}

	attachmentsDir := filepath.Join(vaultPath, "attachments")
	if err := util.EnsureDir(attachmentsDir); err != nil {
		return fmt.Errorf("create attachments dir: %w", err)
	}

	var (
		processed int
		skipped   int
		failed    int
	)

	for _, file := range files {
		fmt.Printf("\nProcessing: %s\n", filepath.Base(file))
		n, err := note.Load(file)
		if err != nil {
			fmt.Printf("  ✗ Failed to read note: %v\n", err)
			failed++
			continue
		}
		title := n.GetTitle()
		fmt.Printf("  Title: %s\n", title)

		needsCover := n.NeedsCover()
		needsMetadata := n.NeedsMetadata()
		needsTMDB := n.NeedsTMDB()

		if !needsCover && !needsMetadata && !needsTMDB && !r.cfg.Force && !r.cfg.GenerateContent {
			fmt.Println("  Already has cover, metadata, and TMDB ID, skipping...")
			skipped++
			continue
		}

		coverURL, meta, err := r.fetchRequiredData(ctx, n, title, needsCover, needsMetadata, needsTMDB)
		if err != nil {
			if errors.Is(err, ErrStopProcessing) {
				fmt.Println("\n⚠️  Processing stopped by user")
				break
			}
			fmt.Printf("  ✗ Error fetching TMDB data: %v\n", err)
			failed++
			continue
		}

		success := false

		if coverURL != "" {
			if err := r.updateCover(ctx, n, coverURL, attachmentsDir); err != nil {
				fmt.Printf("  ✗ %v\n", err)
			} else {
				success = true
			}
		} else if needsCover {
			fmt.Println("  ✗ No cover image found")
		}

		if meta != nil {
			if err := n.UpdateMetadata(r.toNoteMetadata(meta)); err != nil {
				fmt.Printf("  ✗ Failed to update metadata: %v\n", err)
			} else {
				if meta.Runtime != nil {
					fmt.Printf("  ✓ Added runtime: %d minutes\n", *meta.Runtime)
				}
				if meta.TotalEpisodes != nil {
					fmt.Printf("  ✓ Added total episodes: %d\n", *meta.TotalEpisodes)
				}
				if len(meta.GenreTags) > 0 {
					fmt.Printf("  ✓ Added genres: %s\n", strings.Join(meta.GenreTags, ", "))
				}
				if !needsCover {
					success = true
				}
			}
		} else if needsMetadata {
			fmt.Println("  ✗ No metadata found")
		}

		if r.cfg.GenerateContent {
			if err := r.generateContent(ctx, n); err != nil {
				fmt.Printf("  ✗ Failed to generate content: %v\n", err)
			} else {
				success = true
			}
		}

		switch {
		case success:
			processed++
		case coverURL != "" && !needsMetadata:
			processed++
		case meta != nil && !needsCover:
			processed++
		default:
			failed++
		}
	}

	fmt.Println("\n=== Summary ===")
	fmt.Printf("Processed: %d\n", processed)
	fmt.Printf("Skipped: %d\n", skipped)
	fmt.Printf("Failed: %d\n", failed)

	return nil
}

func (r *Runner) fetchRequiredData(
	ctx context.Context,
	n *note.Note,
	title string,
	needsCover, needsMetadata, needsTMDB bool,
) (string, *tmdb.Metadata, error) {
	hasStoredID := false
	tmdbID, hasID := n.GetTMDBID()
	tmdbType, hasType := n.GetTMDBType()
	if hasID && hasType {
		hasStoredID = true
	}

	if hasStoredID && !r.cfg.Force {
		fmt.Printf("  Using stored TMDB ID: %d (%s)\n", tmdbID, tmdbType)
		if !needsCover && !needsMetadata && !needsTMDB {
			return "", nil, nil
		}

		switch {
		case needsCover && needsMetadata:
			if n.HasExternalCover() {
				if existing, ok := n.GetExistingCoverURL(); ok {
					fmt.Println("  Found external cover URL, will download locally")
					meta, err := r.client.GetMetadataByID(ctx, tmdbID, tmdbType)
					return existing, meta, err
				}
			}
			return r.client.GetCoverAndMetadataByID(ctx, tmdbID, tmdbType)
		case needsCover:
			if n.HasExternalCover() {
				if existing, ok := n.GetExistingCoverURL(); ok {
					fmt.Println("  Found external cover URL, will download locally")
					meta, err := r.client.GetMetadataByID(ctx, tmdbID, tmdbType)
					return existing, meta, err
				}
			}
			cover, err := r.client.GetCoverURLByID(ctx, tmdbID, tmdbType)
			if err != nil {
				return "", nil, err
			}
			meta, err := r.client.GetMetadataByID(ctx, tmdbID, tmdbType)
			return cover, meta, err
		case needsMetadata, needsTMDB:
			meta, err := r.client.GetMetadataByID(ctx, tmdbID, tmdbType)
			return "", meta, err
		default:
			return "", nil, nil
		}
	}

	if r.cfg.Force && hasStoredID {
		fmt.Printf("  Force mode: ignoring stored TMDB ID %d (%s)\n", tmdbID, tmdbType)
	}

	results, err := r.client.SearchMulti(ctx, title, 10)
	if err != nil {
		return "", nil, err
	}
	if len(results) == 0 {
		fmt.Println("  No results found")
		return "", nil, nil
	}

	var chosen tmdb.SearchResult
	if len(results) == 1 {
		chosen = results[0]
		mediaLabel := mapMediaType(results[0].MediaType)
		fmt.Printf("  Found %s: %s\n", mediaLabel, results[0].DisplayTitle())
	} else {
		fmt.Printf("  Found %d results, showing selector...\n", len(results))
		selection, err := tui.Select(title, results)
		if err != nil {
			return "", nil, err
		}
		switch selection.Action {
		case tui.ActionSkipped:
			fmt.Println("  Selection skipped by user")
			return "", nil, nil
		case tui.ActionStopped:
			return "", nil, ErrStopProcessing
		case tui.ActionSelected:
			if selection.Selection == nil {
				return "", nil, errors.New("selection missing result")
			}
			chosen = *selection.Selection
			mediaLabel := mapMediaType(chosen.MediaType)
			fmt.Printf("  Selected %s: %s\n", mediaLabel, chosen.DisplayTitle())
		default:
			return "", nil, errors.New("unknown selection action")
		}
	}

	if chosen.PosterPath == "" {
		fmt.Println("  Selected result has no poster")
		return "", nil, nil
	}

	if needsCover && n.HasExternalCover() {
		if existing, ok := n.GetExistingCoverURL(); ok {
			fmt.Println("  Found external cover URL, will download locally")
			meta, err := r.client.GetMetadataByResult(ctx, chosen)
			return existing, meta, err
		}
	}

	return r.client.GetCoverAndMetadataByResult(ctx, chosen)
}

func (r *Runner) updateCover(ctx context.Context, n *note.Note, imageURL, attachmentsDir string) error {
	localPath := n.GenerateLocalCoverPath(attachmentsDir)
	if err := r.client.DownloadAndResizeImage(ctx, imageURL, localPath, 1000); err != nil {
		return fmt.Errorf("failed to download image: %w", err)
	}
	relative, err := n.GetRelativeCoverPath(localPath)
	if err != nil {
		return fmt.Errorf("failed to get relative cover path: %w", err)
	}
	if err := n.UpdateCover(relative); err != nil {
		return fmt.Errorf("failed to update cover: %w", err)
	}
	fmt.Printf("  ✓ Downloaded and updated cover: %s\n", relative)
	return nil
}

func (r *Runner) generateContent(ctx context.Context, n *note.Note) error {
	tmdbID, ok := n.GetTMDBID()
	if !ok {
		return errors.New("no TMDB ID found, cannot generate content")
	}
	tmdbType, ok := n.GetTMDBType()
	if !ok {
		return errors.New("no TMDB type found, cannot generate content")
	}

	var (
		details map[string]any
		err     error
	)

	switch tmdbType {
	case "tv":
		details, err = r.client.GetFullTVDetails(ctx, tmdbID)
	case "movie":
		details, err = r.client.GetFullMovieDetails(ctx, tmdbID)
	default:
		return fmt.Errorf("unsupported TMDB type: %s", tmdbType)
	}
	if err != nil {
		return err
	}
	if len(details) == 0 {
		return errors.New("empty TMDB details")
	}

	sections := r.cfg.ContentSections
	if len(sections) == 0 {
		if tmdbType == "tv" {
			sections = []string{"overview", "info", "seasons"}
		} else {
			sections = []string{"overview", "info"}
		}
	}

	contentText := content.BuildTMDBContent(details, tmdbType, sections)
	if strings.TrimSpace(contentText) == "" {
		return errors.New("no content generated")
	}

	if err := n.UpdateBodyContent(contentText); err != nil {
		return err
	}
	fmt.Printf("  ✓ Generated content sections: %s\n", strings.Join(sections, ", "))
	return nil
}

func (r *Runner) toNoteMetadata(meta *tmdb.Metadata) note.Metadata {
	result := note.Metadata{}
	if meta.Runtime != nil {
		result.Runtime = meta.Runtime
	}
	if meta.TotalEpisodes != nil {
		result.TotalEpisodes = meta.TotalEpisodes
	}
	if len(meta.GenreTags) > 0 {
		result.GenreTags = append([]string(nil), meta.GenreTags...)
	}
	result.TMDBID = &meta.TMDBID
	result.TMDBType = &meta.TMDBType
	return result
}

func mapMediaType(mediaType string) string {
	switch mediaType {
	case "movie":
		return "movie"
	case "tv":
		return "TV show"
	default:
		return mediaType
	}
}
