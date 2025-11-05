// Package util provides file system utility functions.
//
//nolint:revive // util is a common package name for utilities
package util

import (
	"os"
	"path/filepath"
	"strings"
)

// SanitizeFilename removes invalid characters from a filename.
func SanitizeFilename(name string) string {
	invalid := []string{`<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`}
	for _, ch := range invalid {
		name = strings.ReplaceAll(name, ch, "_")
	}
	name = strings.Trim(name, ". ")
	if len(name) > 200 {
		return name[:200]
	}
	return name
}

// EnsureDir creates a directory and all necessary parent directories.
func EnsureDir(path string) error {
	return os.MkdirAll(path, 0o755)
}

// RelativeTo returns the relative path from base to target.
func RelativeTo(base, target string) (string, error) {
	rel, err := filepath.Rel(base, target)
	if err != nil {
		return "", err
	}
	return filepath.ToSlash(rel), nil
}
