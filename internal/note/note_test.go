package note_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/lepinkainen/obsidian-tmdb-cover/internal/note"
)

func TestNoteMetadataUpdates(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.md")
	initial := `---
title: Test Movie
tags:
  - existing-tag
---

# Test Movie

Some content here.
`
	if err := os.WriteFile(path, []byte(initial), 0o644); err != nil {
		t.Fatalf("failed to write note: %v", err)
	}

	n, err := note.Load(path)
	if err != nil {
		t.Fatalf("failed to load note: %v", err)
	}

	runtime := 120
	totalEpisodes := 10
	tmdbID := 9876
	tmdbType := "movie"

	meta := note.Metadata{
		Runtime:       &runtime,
		TotalEpisodes: &totalEpisodes,
		GenreTags:     []string{"movie/Action", "movie/Adventure"},
		TMDBID:        &tmdbID,
		TMDBType:      &tmdbType,
	}

	if err := n.UpdateMetadata(meta); err != nil {
		t.Fatalf("update metadata failed: %v", err)
	}

	reloaded, err := note.Load(path)
	if err != nil {
		t.Fatalf("failed to reload note: %v", err)
	}

	if value, ok := reloaded.Frontmatter()["runtime"].(int); !ok || value != runtime {
		t.Fatalf("expected runtime %d, got %#v", runtime, reloaded.Frontmatter()["runtime"])
	}

	if value, ok := reloaded.Frontmatter()["total_episodes"].(int); !ok || value != totalEpisodes {
		t.Fatalf("expected total episodes %d, got %#v", totalEpisodes, reloaded.Frontmatter()["total_episodes"])
	}

	rawTags := reloaded.Frontmatter()["tags"]
	var tags []string
	switch v := rawTags.(type) {
	case []any:
		for _, item := range v {
			if s, ok := item.(string); ok {
				tags = append(tags, s)
			}
		}
	case []string:
		tags = append(tags, v...)
	}
	wantTags := map[string]struct{}{
		"existing-tag":    {},
		"movie/Action":    {},
		"movie/Adventure": {},
	}
	for _, tag := range tags {
		delete(wantTags, tag)
	}
	if len(wantTags) != 0 {
		t.Fatalf("missing tags: %v", wantTags)
	}

	if id, ok := reloaded.GetTMDBID(); !ok || id != tmdbID {
		t.Fatalf("expected tmdb id %d, got %d", tmdbID, id)
	}
	if typ, ok := reloaded.GetTMDBType(); !ok || typ != tmdbType {
		t.Fatalf("expected tmdb type %s, got %s", tmdbType, typ)
	}

	content := "## Overview\n\nTest overview"
	if err := reloaded.UpdateBodyContent(content); err != nil {
		t.Fatalf("update body content failed: %v", err)
	}

	finalNote, err := note.Load(path)
	if err != nil {
		t.Fatalf("failed to load note after body update: %v", err)
	}
	if !finalNote.HasTMDBContentMarkers() {
		t.Fatalf("expected TMDB markers to be injected")
	}
}
