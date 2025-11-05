// Package note provides Obsidian markdown note parsing and manipulation.
package note

import (
	"errors"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/lepinkainen/obsidian-tmdb-cover/internal/util"
)

const (
	startMarker = "<!-- TMDB_DATA_START -->"
	endMarker   = "<!-- TMDB_DATA_END -->"
)

var (
	frontMatterDelimiter = "---"
	htmlColorPattern     = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)
)

// Metadata holds TMDB metadata to be added to a note.
type Metadata struct {
	Runtime       *int
	TotalEpisodes *int
	GenreTags     []string
	TMDBID        *int
	TMDBType      *string
}

// Note represents an Obsidian markdown note with frontmatter and body.
type Note struct {
	Path        string
	frontmatter map[string]any
	body        string
}

// Load reads and parses an Obsidian note from disk.
func Load(path string) (*Note, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	content := string(data)
	n := &Note{
		Path:        path,
		frontmatter: make(map[string]any),
		body:        content,
	}

	if !strings.HasPrefix(content, frontMatterDelimiter) {
		n.body = content
		return n, nil
	}

	trimmed := strings.TrimPrefix(content, frontMatterDelimiter)
	trimmed = strings.TrimPrefix(trimmed, "\n")
	parts := strings.SplitN(trimmed, "\n"+frontMatterDelimiter+"\n", 2)
	if len(parts) != 2 {
		// malformed frontmatter; treat entire file as body
		n.body = content
		return n, nil
	}

	fm := strings.TrimSuffix(parts[0], "\n")
	body := parts[1]

	if err := yaml.Unmarshal([]byte(fm), &n.frontmatter); err != nil {
		// leave frontmatter empty, treat as body
		n.frontmatter = make(map[string]any)
		n.body = content
		return n, nil
	}

	n.body = body
	return n, nil
}

// Frontmatter returns the note's frontmatter as a map.
func (n *Note) Frontmatter() map[string]any {
	return n.frontmatter
}

// Body returns the note's body content.
func (n *Note) Body() string {
	return n.body
}

// GetTitle extracts the note title from frontmatter, H1 header, or filename.
func (n *Note) GetTitle() string {
	if title, ok := n.frontmatter["title"].(string); ok && title != "" {
		return title
	}

	lines := strings.Split(n.body, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "# ") {
			return strings.TrimSpace(line[2:])
		}
	}

	return strings.TrimSuffix(filepath.Base(n.Path), filepath.Ext(n.Path))
}

func (n *Note) hasCover() (string, bool) {
	value, ok := n.frontmatter["cover"]
	if !ok {
		return "", false
	}
	cover, ok := value.(string)
	if !ok || cover == "" {
		return "", false
	}
	return cover, true
}

// HasExternalCover returns true if the note has an external HTTP(S) cover URL.
func (n *Note) HasExternalCover() bool {
	cover, ok := n.hasCover()
	if !ok {
		return false
	}
	if htmlColorPattern.MatchString(cover) {
		return false
	}
	return strings.HasPrefix(cover, "http")
}

// GetExistingCoverURL returns the external cover URL if present.
func (n *Note) GetExistingCoverURL() (string, bool) {
	if n.HasExternalCover() {
		cover, _ := n.hasCover()
		return cover, true
	}
	return "", false
}

// GenerateLocalCoverPath generates a local path for the cover image.
func (n *Note) GenerateLocalCoverPath(attachmentsDir string) string {
	title := n.GetTitle()
	filename := util.SanitizeFilename(title + " - cover.jpg")
	return filepath.Join(attachmentsDir, filename)
}

// GetRelativeCoverPath returns the relative path from the note to the cover.
func (n *Note) GetRelativeCoverPath(localPath string) (string, error) {
	noteDir := filepath.Dir(n.Path)
	return util.RelativeTo(noteDir, localPath)
}

// UpdateCover updates the note's cover path in frontmatter.
func (n *Note) UpdateCover(path string) error {
	n.frontmatter["cover"] = path
	return n.save()
}

// UpdateMetadata updates the note's TMDB metadata in frontmatter.
func (n *Note) UpdateMetadata(meta Metadata) error {
	if meta.Runtime != nil {
		n.frontmatter["runtime"] = *meta.Runtime
	}
	if meta.TotalEpisodes != nil {
		n.frontmatter["total_episodes"] = *meta.TotalEpisodes
	}
	if len(meta.GenreTags) > 0 {
		existing := n.getTags()
		tagSet := make(map[string]struct{}, len(existing)+len(meta.GenreTags))
		for _, t := range existing {
			tagSet[t] = struct{}{}
		}
		for _, t := range meta.GenreTags {
			tagSet[t] = struct{}{}
		}
		merged := make([]string, 0, len(tagSet))
		for tag := range tagSet {
			merged = append(merged, tag)
		}
		sort.Strings(merged)
		n.frontmatter["tags"] = merged
	}
	if meta.TMDBID != nil {
		n.frontmatter["tmdb_id"] = *meta.TMDBID
	}
	if meta.TMDBType != nil {
		n.frontmatter["tmdb_type"] = *meta.TMDBType
	}
	return n.save()
}

// UpdateBodyContent updates or injects TMDB content into the note body.
func (n *Note) UpdateBodyContent(content string) error {
	body := strings.TrimSpace(content)
	if body == "" {
		return errors.New("empty content")
	}

	if n.HasTMDBContentMarkers() {
		startIdx := strings.Index(n.body, startMarker)
		endIdx := strings.Index(n.body, endMarker)
		if startIdx != -1 && endIdx != -1 && endIdx > startIdx {
			before := strings.TrimSpace(n.body[:startIdx])
			after := strings.TrimSpace(n.body[endIdx+len(endMarker):])

			var builder strings.Builder
			if before != "" {
				builder.WriteString(before)
				builder.WriteString("\n\n")
			}
			builder.WriteString(startMarker)
			builder.WriteString("\n")
			builder.WriteString(body)
			builder.WriteString("\n")
			builder.WriteString(endMarker)
			if after != "" {
				builder.WriteString("\n")
				builder.WriteString(after)
			}
			n.body = builder.String()
			return n.save()
		}
	}
	return n.injectTMDBMarkers(body)
}

// HasTMDBContentMarkers returns true if the note contains TMDB content markers.
func (n *Note) HasTMDBContentMarkers() bool {
	return strings.Contains(n.body, startMarker) && strings.Contains(n.body, endMarker)
}

// GetTMDBID returns the TMDB ID stored in the note's frontmatter.
func (n *Note) GetTMDBID() (int, bool) {
	id, ok := n.frontmatter["tmdb_id"]
	if !ok {
		return 0, false
	}
	switch v := id.(type) {
	case int:
		return v, true
	case int64:
		return int(v), true
	case float64:
		return int(v), true
	default:
		return 0, false
	}
}

// GetTMDBType returns the TMDB type (movie or tv) stored in frontmatter.
func (n *Note) GetTMDBType() (string, bool) {
	value, ok := n.frontmatter["tmdb_type"].(string)
	if !ok {
		return "", false
	}
	value = strings.TrimSpace(value)
	if value != "movie" && value != "tv" {
		return "", false
	}
	return value, true
}

// AttachmentsDir returns the attachments directory for this note.
func (n *Note) AttachmentsDir(basePath string) (string, error) {
	attachments := filepath.Join(basePath, "attachments")
	return attachments, util.EnsureDir(attachments)
}

func (n *Note) save() error {
	var builder strings.Builder
	builder.WriteString(frontMatterDelimiter)
	builder.WriteString("\n")

	if len(n.frontmatter) > 0 {
		data, err := yaml.Marshal(n.frontmatter)
		if err != nil {
			return err
		}
		builder.Write(data)
		if !strings.HasSuffix(builder.String(), "\n") {
			builder.WriteString("\n")
		}
	}

	builder.WriteString(frontMatterDelimiter)
	builder.WriteString("\n")
	builder.WriteString(strings.TrimLeft(n.body, "\n"))
	if !strings.HasSuffix(builder.String(), "\n") {
		builder.WriteString("\n")
	}

	if err := os.WriteFile(n.Path, []byte(builder.String()), 0o644); err != nil {
		return err
	}
	// refresh body/frontmatter to reflect canonical formatting
	updated, err := Load(n.Path)
	if err != nil {
		return err
	}
	n.frontmatter = updated.frontmatter
	n.body = updated.body
	return nil
}

func (n *Note) getTags() []string {
	value, ok := n.frontmatter["tags"]
	if !ok {
		return nil
	}
	switch v := value.(type) {
	case []any:
		result := make([]string, 0, len(v))
		for _, item := range v {
			if s, ok := item.(string); ok && s != "" {
				result = append(result, s)
			}
		}
		return result
	case []string:
		return append([]string(nil), v...)
	default:
		return nil
	}
}

func (n *Note) injectTMDBMarkers(content string) error {
	var builder strings.Builder
	body := strings.TrimRight(n.body, "\n")
	if body != "" {
		builder.WriteString(body)
		builder.WriteString("\n\n")
	}
	builder.WriteString(startMarker)
	builder.WriteString("\n")
	builder.WriteString(content)
	builder.WriteString("\n")
	builder.WriteString(endMarker)
	builder.WriteString("\n")
	n.body = builder.String()
	return n.save()
}

// NeedsCover returns true if the note needs a cover image.
func (n *Note) NeedsCover() bool {
	cover, ok := n.hasCover()
	if !ok || cover == "" {
		return true
	}
	if htmlColorPattern.MatchString(cover) {
		return true
	}
	if strings.HasPrefix(cover, "http") {
		return true
	}
	return false
}

// NeedsMetadata returns true if the note needs TMDB metadata.
func (n *Note) NeedsMetadata() bool {
	if _, ok := n.frontmatter["runtime"]; !ok {
		return true
	}

	// Check for existing genre tags
	for _, tag := range n.getTags() {
		if strings.HasPrefix(tag, "movie/") || strings.HasPrefix(tag, "tv/") {
			return false
		}
	}
	return true
}

// NeedsTMDB returns true if the note needs TMDB ID and type stored.
func (n *Note) NeedsTMDB() bool {
	_, hasID := n.GetTMDBID()
	_, hasType := n.GetTMDBType()
	return !hasID || !hasType
}
