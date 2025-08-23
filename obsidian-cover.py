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
from PIL import Image
from io import BytesIO


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Limit length
    if len(filename) > 200:
        filename = filename[:200]

    return filename


def create_attachments_dir(base_dir: Path) -> Path:
    """Create and return the attachments directory path"""
    attachments_dir = base_dir / "attachments"
    attachments_dir.mkdir(exist_ok=True)
    return attachments_dir


class TMDBCoverFetcher:
    def __init__(self, api_key: str):
        """Initialize with TMDB API key"""
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self._genre_cache: Dict[str, Dict[int, str]] = {}

    def _sanitize_genre_name(self, name: str) -> str:
        """Sanitize genre name for valid Obsidian tags"""
        # Replace common problematic characters
        sanitized = name.replace("&", "and")
        # Remove or replace other characters that might cause issues
        sanitized = sanitized.replace("#", "")  # Remove hash symbols
        sanitized = sanitized.replace("/", "-")  # Replace slashes with hyphens
        sanitized = sanitized.replace(" ", "-")  # Replace spaces with hyphens
        return sanitized.strip("-")  # Remove leading/trailing hyphens

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

    def _get_genres(self, media_type: str) -> Dict[int, str]:
        """Get genre mapping for movie or tv, with caching"""
        if media_type in self._genre_cache:
            return self._genre_cache[media_type]

        url = f"{self.base_url}/genre/{media_type}/list"
        params = {"api_key": self.api_key}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            genres = {}
            for genre in data.get("genres", []):
                genres[genre["id"]] = genre["name"]

            self._genre_cache[media_type] = genres
            return genres

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {media_type} genres: {e}")
            return {}

    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed movie information"""
        url = f"{self.base_url}/movie/{movie_id}"
        params = {"api_key": self.api_key}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching movie details: {e}")
            return None

    def get_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed TV show information"""
        url = f"{self.base_url}/tv/{tv_id}"
        params = {"api_key": self.api_key}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching TV details: {e}")
            return None

    def get_metadata(self, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata (runtime, genres) from search result"""
        media_type = search_result.get("media_type")
        media_id = search_result.get("id")

        if not media_type or not media_id:
            return {}

        details = None
        if media_type == "movie":
            details = self.get_movie_details(media_id)
        elif media_type == "tv":
            details = self.get_tv_details(media_id)

        if not details:
            return {}

        metadata = {}

        # Extract runtime
        if media_type == "movie":
            runtime = details.get("runtime")
            if runtime:
                metadata["runtime"] = runtime
        elif media_type == "tv":
            episode_run_time = details.get("episode_run_time")
            if episode_run_time and len(episode_run_time) > 0:
                metadata["runtime"] = episode_run_time[0]
            else:
                # Debug logging for missing runtime data
                if episode_run_time is None:
                    print("  ℹ No episode_run_time field in API response")
                elif isinstance(episode_run_time, list) and len(episode_run_time) == 0:
                    print("  ℹ episode_run_time is empty array")
                else:
                    print(f"  ℹ episode_run_time value: {episode_run_time}")

        # Extract and format genres
        genre_ids = [g["id"] for g in details.get("genres", [])]
        if genre_ids:
            genre_mapping = self._get_genres(media_type)
            genre_tags = []
            for genre_id in genre_ids:
                if genre_id in genre_mapping:
                    genre_name = genre_mapping[genre_id]
                    # Sanitize genre name for valid Obsidian tags
                    sanitized_name = self._sanitize_genre_name(genre_name)
                    genre_tag = f"{media_type}/{sanitized_name}"
                    genre_tags.append(genre_tag)

            if genre_tags:
                metadata["genre_tags"] = genre_tags

        return metadata

    def download_and_resize_image(
        self, image_url: str, save_path: Path, max_width: int = 1000
    ) -> bool:
        """
        Download an image from URL, resize it, and save to local path
        Returns True if successful, False otherwise
        """
        try:
            # Download the image
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            # Open image with PIL
            image = Image.open(BytesIO(response.content))  # type: ignore

            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode != "RGB":
                image = image.convert("RGB")  # type: ignore

            # Calculate new dimensions maintaining aspect ratio
            width, height = image.size
            if width > max_width:
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)  # type: ignore

            # Save as JPEG with good quality
            image.save(save_path, "JPEG", quality=85, optimize=True)
            return True

        except Exception as e:
            print(f"  Error downloading/resizing image: {e}")
            return False

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

    def get_cover_and_metadata(
        self, title: str
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Get both cover URL and metadata for a movie/TV show title"""
        result = self.search_multi(title)

        if not result or not result.get("poster_path"):
            return None, {}

        cover_url = f"{self.image_base_url}{result['poster_path']}"
        media_type = "movie" if result.get("media_type") == "movie" else "TV show"
        name = result.get("title") or result.get("name", "Unknown")
        print(f"  Found {media_type}: {name}")

        metadata = self.get_metadata(result)
        return cover_url, metadata


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
            # If relative_to fails, use the full path
            return str(local_path)

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

        if "genre_tags" in metadata:
            existing_tags = self.frontmatter.get("tags", [])
            if not isinstance(existing_tags, list):
                existing_tags = []

            # Merge tags, avoiding duplicates
            all_tags = list(set(existing_tags + metadata["genre_tags"]))
            all_tags.sort()
            self.frontmatter["tags"] = all_tags

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

    # Create attachments directory
    attachments_dir = create_attachments_dir(vault_path)

    for file_path in md_files:
        print(f"\nProcessing: {file_path.name}")

        try:
            note = ObsidianNoteUpdater(str(file_path))
            title = note.get_title()
            print(f"  Title: {title}")

            # Check current cover status
            existing_cover = note.frontmatter.get("cover")

            # Check if we need to fetch a cover
            needs_cover = (
                not existing_cover
                or note._is_html_color_code(existing_cover)
                or note.has_external_cover()
            )

            # Check if we need to fetch metadata
            existing_runtime = note.frontmatter.get("runtime")
            existing_tags = note.frontmatter.get("tags", [])
            has_genre_tags = any(
                tag.startswith(("movie/", "tv/"))
                for tag in existing_tags
                if isinstance(tag, str)
            )
            needs_metadata = not existing_runtime or not has_genre_tags

            # Skip if we don't need cover or metadata
            if not needs_cover and not needs_metadata:
                print("  Already has cover and metadata, skipping...")
                skipped += 1
                continue

            # Determine what to fetch
            image_url = None
            metadata = {}

            if needs_cover and needs_metadata:
                if note.has_external_cover():
                    # Download existing external URL, but also fetch metadata
                    image_url = note.get_existing_cover_url()
                    print("  Found external cover URL, will download locally")
                    # Still need to search for metadata
                    _, metadata = tmdb.get_cover_and_metadata(title)
                elif existing_cover and note._is_html_color_code(existing_cover):
                    print(f"  Replacing color placeholder: {existing_cover}")
                    # Search for new cover and metadata
                    image_url, metadata = tmdb.get_cover_and_metadata(title)
                elif not existing_cover:
                    # No cover, search for one and get metadata
                    image_url, metadata = tmdb.get_cover_and_metadata(title)
            elif needs_cover:
                # Only need cover
                if note.has_external_cover():
                    image_url = note.get_existing_cover_url()
                    print("  Found external cover URL, will download locally")
                elif existing_cover and note._is_html_color_code(existing_cover):
                    print(f"  Replacing color placeholder: {existing_cover}")
                    image_url = tmdb.get_cover_url(title)
                elif not existing_cover:
                    image_url = tmdb.get_cover_url(title)
            elif needs_metadata:
                # Only need metadata
                print("  Fetching metadata only...")
                _, metadata = tmdb.get_cover_and_metadata(title)

            success = False

            if image_url:
                # Generate local path for the cover
                local_cover_path = note.generate_local_cover_path(attachments_dir)

                # Download and resize the image
                if tmdb.download_and_resize_image(image_url, local_cover_path):
                    # Update note with relative path
                    relative_path = note.get_relative_cover_path(local_cover_path)

                    if note.update_cover(relative_path):
                        print(f"  ✓ Downloaded and updated cover: {relative_path}")
                        success = True
                    else:
                        print("  ✗ Failed to update cover")
                else:
                    print("  ✗ Failed to download image")

            elif needs_cover:
                print("  ✗ No cover image found")

            # Update metadata if we have it (regardless of cover success)
            if metadata:
                if note.update_metadata(metadata):
                    runtime = metadata.get("runtime")
                    genre_tags = metadata.get("genre_tags", [])
                    if runtime:
                        print(f"  ✓ Added runtime: {runtime} minutes")
                    if genre_tags:
                        print(f"  ✓ Added genres: {', '.join(genre_tags)}")

                    # If we only needed metadata, this counts as success
                    if not needs_cover:
                        success = True
                else:
                    print("  ✗ Failed to update metadata")
            elif needs_metadata:
                print("  ✗ No metadata found")

            if (
                success
                or (image_url and not needs_metadata)
                or (metadata and not needs_cover)
            ):
                processed += 1
            else:
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
