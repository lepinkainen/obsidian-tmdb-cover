"""Obsidian note updater for managing markdown files with YAML frontmatter."""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from .utils import sanitize_filename


class ObsidianNoteUpdater:
    def __init__(self, file_path: str):
        """Initialize with path to Obsidian markdown file"""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.content = self.file_path.read_text(encoding="utf-8")
        self.frontmatter: Dict[str, Any] = {}
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

    def has_external_cover(self) -> bool:
        """Check if the note has an external URL as cover"""
        cover = self.frontmatter.get("cover")
        if not cover or self._is_html_color_code(cover):
            return False

        # Check if it's an external URL (starts with http)
        return isinstance(cover, str) and cover.startswith("http")

    def get_existing_cover_url(self) -> Optional[str]:
        """Get the existing cover URL if it's external"""
        if self.has_external_cover():
            return self.frontmatter.get("cover")
        return None

    def generate_local_cover_path(self, attachments_dir: Path) -> Path:
        """Generate the local path for the cover image"""
        title = self.get_title()
        safe_filename = sanitize_filename(f"{title} - cover.jpg")
        return attachments_dir / safe_filename

    def get_relative_cover_path(self, local_path: Path) -> str:
        """Get the relative path from the note to the cover image"""
        try:
            # Get relative path from note's directory to the image
            note_dir = self.file_path.parent
            relative_path = local_path.relative_to(note_dir)
            return str(relative_path).replace("\\", "/")  # Use forward slashes
        except ValueError:
            # If relative_to fails, compute path relative to the note's directory
            # This handles cases where attachments folder is outside note's directory
            import os

            relative_path_str = os.path.relpath(local_path, note_dir)
            return relative_path_str.replace("\\", "/")

    def update_cover(self, cover_path: str) -> bool:
        """Add or update the cover property in frontmatter"""
        self.frontmatter["cover"] = cover_path
        return self._save_file()

    def update_runtime(self, runtime: int) -> bool:
        """Add or update the runtime property in frontmatter"""
        self.frontmatter["runtime"] = runtime
        return self._save_file()

    def update_tags(self, new_tags: list[str]) -> bool:
        """Add new tags to existing tags in frontmatter"""
        existing_tags = self.frontmatter.get("tags", [])

        # Ensure existing_tags is a list
        if not isinstance(existing_tags, list):
            existing_tags = []

        # Merge tags, avoiding duplicates
        all_tags = list(set(existing_tags + new_tags))
        all_tags.sort()  # Sort for consistency

        self.frontmatter["tags"] = all_tags
        return self._save_file()

    def update_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Update multiple metadata fields at once"""
        if "runtime" in metadata:
            self.frontmatter["runtime"] = metadata["runtime"]

        if "total_episodes" in metadata:
            self.frontmatter["total_episodes"] = metadata["total_episodes"]

        if "genre_tags" in metadata:
            existing_tags = self.frontmatter.get("tags", [])
            if not isinstance(existing_tags, list):
                existing_tags = []

            # Merge tags, avoiding duplicates
            all_tags = list(set(existing_tags + metadata["genre_tags"]))
            all_tags.sort()
            self.frontmatter["tags"] = all_tags

        if "tmdb_id" in metadata:
            self.frontmatter["tmdb_id"] = metadata["tmdb_id"]

        if "tmdb_type" in metadata:
            self.frontmatter["tmdb_type"] = metadata["tmdb_type"]

        return self._save_file()

    def get_tmdb_id(self) -> Optional[int]:
        """Get stored TMDB ID from frontmatter"""
        tmdb_id = self.frontmatter.get("tmdb_id")
        if tmdb_id and isinstance(tmdb_id, int):
            return tmdb_id
        return None

    def get_tmdb_type(self) -> Optional[str]:
        """Get stored TMDB type (movie or tv) from frontmatter"""
        tmdb_type = self.frontmatter.get("tmdb_type")
        if tmdb_type in ["movie", "tv"]:
            return tmdb_type
        return None

    def has_tmdb_content_markers(self) -> bool:
        """Check if body already has TMDB content markers"""
        return "<!-- TMDB_DATA_START -->" in self.body

    def update_body_content(self, tmdb_content: str) -> bool:
        """Update/inject TMDB content in body between markers"""
        start_marker = "<!-- TMDB_DATA_START -->"
        end_marker = "<!-- TMDB_DATA_END -->"

        if self.has_tmdb_content_markers():
            # Replace content between markers
            # Find start and end marker positions
            start_idx = self.body.find(start_marker)
            end_idx = self.body.find(end_marker)

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # Preserve content before start marker
                before = self.body[:start_idx].rstrip()
                # Preserve content after end marker (if any)
                after = self.body[end_idx + len(end_marker) :].lstrip()

                # Reconstruct body with new TMDB content
                new_body = f"{before}\n\n{start_marker}\n{tmdb_content}\n{end_marker}"
                if after:
                    new_body += f"\n{after}"

                self.body = new_body
            else:
                # Malformed markers, append new content
                return self.inject_tmdb_markers(tmdb_content)
        else:
            # No markers exist, inject them
            return self.inject_tmdb_markers(tmdb_content)

        return self._save_file()

    def inject_tmdb_markers(self, tmdb_content: str) -> bool:
        """Add markers and content to body for first time"""
        start_marker = "<!-- TMDB_DATA_START -->"
        end_marker = "<!-- TMDB_DATA_END -->"

        # Ensure body has proper spacing
        body_stripped = self.body.rstrip()

        # Add markers with content
        if body_stripped:
            # User has existing content, add after it
            self.body = (
                f"{body_stripped}\n\n{start_marker}\n{tmdb_content}\n{end_marker}\n"
            )
        else:
            # Empty body, just add markers
            self.body = f"{start_marker}\n{tmdb_content}\n{end_marker}\n"

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
