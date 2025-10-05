"""Command-line interface for obsidian-tmdb-cover."""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from .fetcher import TMDBCoverFetcher
from .updater import ObsidianNoteUpdater
from .utils import create_attachments_dir


def _determine_processing_needs(note: ObsidianNoteUpdater) -> tuple[bool, bool]:
    """Determine if note needs cover and/or metadata"""
    # Check if we need to fetch a cover
    existing_cover = note.frontmatter.get("cover")
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

    return needs_cover, needs_metadata


def _fetch_required_data(
    fetcher: TMDBCoverFetcher,
    note: ObsidianNoteUpdater,
    title: str,
    needs_cover: bool,
    needs_metadata: bool,
) -> tuple[Optional[str], Dict[str, Any]]:
    """Fetch cover URL and/or metadata based on needs"""
    image_url = None
    metadata: Dict[str, Any] = {}
    existing_cover = note.frontmatter.get("cover")

    if needs_cover and needs_metadata:
        if note.has_external_cover():
            image_url = note.get_existing_cover_url()
            print("  Found external cover URL, will download locally")
            _, metadata = fetcher.get_cover_and_metadata(title)
        elif existing_cover and note._is_html_color_code(existing_cover):
            print(f"  Replacing color placeholder: {existing_cover}")
            image_url, metadata = fetcher.get_cover_and_metadata(title)
        elif not existing_cover:
            image_url, metadata = fetcher.get_cover_and_metadata(title)
    elif needs_cover:
        if note.has_external_cover():
            image_url = note.get_existing_cover_url()
            print("  Found external cover URL, will download locally")
        elif existing_cover and note._is_html_color_code(existing_cover):
            print(f"  Replacing color placeholder: {existing_cover}")
            image_url = fetcher.get_cover_url(title)
        elif not existing_cover:
            image_url = fetcher.get_cover_url(title)
    elif needs_metadata:
        print("  Fetching metadata only...")
        _, metadata = fetcher.get_cover_and_metadata(title)

    return image_url, metadata


def main() -> None:
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
        sys.exit(1)

    vault_path = Path(args.directory)

    if not vault_path.exists():
        print(f"Path does not exist: {vault_path}")
        sys.exit(1)

    if not vault_path.is_dir():
        print(f"Path is not a directory: {vault_path}")
        sys.exit(1)

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files")

    if len(md_files) == 0:
        print("No markdown files found in the directory")
        sys.exit(1)

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

            # Determine what the note needs
            needs_cover, needs_metadata = _determine_processing_needs(note)

            # Skip if we don't need cover or metadata
            if not needs_cover and not needs_metadata:
                print("  Already has cover and metadata, skipping...")
                skipped += 1
                continue

            # Fetch required data
            image_url, metadata = _fetch_required_data(
                tmdb, note, title, needs_cover, needs_metadata
            )

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
