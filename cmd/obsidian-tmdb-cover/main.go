// Package main provides the CLI entry point for obsidian-tmdb-cover.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/lepinkainen/obsidian-tmdb-cover/internal/app"
	"github.com/lepinkainen/obsidian-tmdb-cover/internal/tmdb"
)

func main() {
	var (
		force           bool
		generateContent bool
		contentSections string
	)

	flag.BoolVar(&force, "force", false, "Force re-search even if TMDB ID is already stored")
	flag.BoolVar(&force, "f", false, "Force re-search even if TMDB ID is already stored (shorthand)")
	flag.BoolVar(&generateContent, "generate-content", false, "Generate TMDB content sections in note body")
	flag.BoolVar(&generateContent, "g", false, "Generate TMDB content sections in note body (shorthand)")
	flag.StringVar(&contentSections, "content-sections", "overview,info,seasons", "Comma-separated list of sections to generate")

	flag.Usage = func() {
		_, _ = fmt.Fprintf(flag.CommandLine.Output(), "Usage: %s [options] <path>\n", os.Args[0])
		flag.PrintDefaults()
	}

	flag.Parse()

	args := flag.Args()
	if len(args) == 0 {
		flag.Usage()
		os.Exit(1)
	}
	inputPath := args[0]

	apiKey := strings.TrimSpace(os.Getenv("TMDB_API_KEY"))
	if apiKey == "" {
		fmt.Println("Error: TMDB_API_KEY environment variable is not set")
		fmt.Println("Please set your TMDB API key as an environment variable, e.g.:")
		fmt.Println("  export TMDB_API_KEY=your_api_key_here")
		os.Exit(1)
	}

	client := tmdb.NewClient(apiKey)
	cfg := app.Config{
		Path:            inputPath,
		Force:           force,
		GenerateContent: generateContent,
	}

	if generateContent && strings.TrimSpace(contentSections) != "" {
		cfg.ContentSections = splitSections(contentSections)
	}

	runner := app.NewRunner(client, cfg)
	if err := runner.Run(context.Background()); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func splitSections(value string) []string {
	parts := strings.Split(value, ",")
	sections := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			sections = append(sections, trimmed)
		}
	}
	return sections
}
