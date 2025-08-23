#!/usr/bin/env python3
"""
Obsidian TMDB Cover Image Script
Processes all markdown files in a directory to add movie/TV show cover images from TheMovieDB

Usage: python obsidian-cover.py <directory_path>
"""

import os
import re
import argparse
import requests
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class TMDBCoverFetcher:
    def __init__(self, api_key: str):
        """Initialize with TMDB API key"""
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"

    def search_multi(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for movies and TV shows simultaneously
        Returns the first result with a poster
        """
        url = f"{self.base_url}/search/multi"
        params = {"api_key": self.api_key, "query": query, "include_adult": "false"}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Filter results to only movies and TV shows with posters
            for result in data.get("results", []):
                if result.get("media_type") in ["movie", "tv"] and result.get(
                    "poster_path"
                ):
                    return result

            return None

        except requests.exceptions.RequestException as e:
            print(f"Error searching TMDB: {e}")
            return None

    def get_cover_url(self, title: str) -> Optional[str]:
        """Get the cover image URL for a movie/TV show title"""
        result = self.search_multi(title)

        if result and result.get("poster_path"):
            cover_url = f"{self.image_base_url}{result['poster_path']}"
            media_type = "movie" if result.get("media_type") == "movie" else "TV show"
            name = result.get("title") or result.get("name", "Unknown")
            print(f"  Found {media_type}: {name}")
            return cover_url

        return None


class ObsidianNoteUpdater:
    def __init__(self, file_path: str):
        """Initialize with path to Obsidian markdown file"""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.content = self.file_path.read_text(encoding="utf-8")
        self.frontmatter = {}
        self.body = ""
        self._parse_content()

    def _is_html_color_code(self, value: str) -> bool:
        """Check if a string is an HTML color code in #xxxxxx format"""
        if not isinstance(value, str):
            return False
        return bool(re.match(r"^#[0-9a-fA-F]{6}$", value))

    def _parse_content(self):
        """Parse the markdown file to extract frontmatter and body"""
        # Check if file has frontmatter
        if self.content.startswith("---\n"):
            # Find the closing --- for frontmatter
            pattern = r"^---\n(.*?)\n---\n(.*)$"
            match = re.match(pattern, self.content, re.DOTALL)

            if match:
                frontmatter_str = match.group(1)
                self.body = match.group(2)

                # Parse YAML frontmatter
                try:
                    self.frontmatter = yaml.safe_load(frontmatter_str) or {}
                except yaml.YAMLError:
                    self.frontmatter = {}
            else:
                # Malformed frontmatter, treat whole content as body
                self.body = self.content
        else:
            # No frontmatter
            self.body = self.content

    def get_title(self) -> str:
        """
        Get the title of the note
        Priority: 1. Title from frontmatter, 2. First H1 heading, 3. Filename
        """
        # Check frontmatter for title
        if self.frontmatter.get("title"):
            return self.frontmatter["title"]

        # Check for H1 heading in body
        h1_match = re.search(r"^#\s+(.+)$", self.body, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Use filename without extension
        return self.file_path.stem

    def update_cover(self, cover_url: str) -> bool:
        """Add or update the cover property in frontmatter"""
        self.frontmatter["cover"] = cover_url
        return self._save_file()

    def _save_file(self) -> bool:
        """Save the updated content back to the file"""
        try:
            # Reconstruct the file content
            frontmatter_str = yaml.dump(
                self.frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

            # Remove trailing newline from yaml.dump
            frontmatter_str = frontmatter_str.rstrip("\n")

            # Reconstruct full content
            new_content = f"---\n{frontmatter_str}\n---\n{self.body}"

            # Write back to file
            self.file_path.write_text(new_content, encoding="utf-8")
            return True

        except Exception as e:
            print(f"Error saving file: {e}")
            return False


def main():
    """Process all markdown files in a directory"""
    parser = argparse.ArgumentParser(
        description="Add TMDB cover images to Obsidian notes"
    )
    parser.add_argument(
        "directory", help="Path to Obsidian vault or folder containing markdown files"
    )

    args = parser.parse_args()

    API_KEY = os.getenv("TMDB_API_KEY")
    if not API_KEY:
        print("Error: TMDB_API_KEY environment variable is not set")
        print("Please set your TMDB API key as an environment variable:")
        print("  export TMDB_API_KEY=your_api_key_here")
        return

    vault_path = Path(args.directory.strip('"').strip("'"))

    if not vault_path.exists():
        print(f"Path does not exist: {vault_path}")
        return

    if not vault_path.is_dir():
        print(f"Path is not a directory: {vault_path}")
        return

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files")

    if len(md_files) == 0:
        print("No markdown files found in the directory")
        return

    tmdb = TMDBCoverFetcher(API_KEY)
    processed = 0
    skipped = 0
    failed = 0

    for file_path in md_files:
        print(f"\nProcessing: {file_path.name}")

        try:
            note = ObsidianNoteUpdater(str(file_path))

            # Skip if already has cover (unless it's a color code placeholder)
            existing_cover = note.frontmatter.get("cover")
            if existing_cover and not note._is_html_color_code(existing_cover):
                print("  Already has cover, skipping...")
                skipped += 1
                continue

            # Check if we're replacing a color code
            if existing_cover and note._is_html_color_code(existing_cover):
                print(f"  Replacing color placeholder: {existing_cover}")

            title = note.get_title()
            print(f"  Title: {title}")

            cover_url = tmdb.get_cover_url(title)

            if cover_url:
                if note.update_cover(cover_url):
                    print("  ✓ Updated successfully")
                    processed += 1
                else:
                    print("  ✗ Failed to update")
                    failed += 1
            else:
                print("  ✗ No results found")
                failed += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

    print("\n=== Summary ===")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    print("Obsidian TMDB Cover Image Updater")
    print("-" * 32)
    main()
