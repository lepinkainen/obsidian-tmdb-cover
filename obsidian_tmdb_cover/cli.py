"""Command-line interface for obsidian-tmdb-cover."""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from .fetcher import TMDBCoverFetcher
from .updater import ObsidianNoteUpdater
from .utils import create_attachments_dir
from .tui import select_tmdb_result


def _determine_processing_needs(
    note: ObsidianNoteUpdater,
) -> tuple[bool, bool, bool]:
    """Determine if note needs cover, metadata, and/or TMDB ID"""
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

    # Check if we need to store TMDB ID
    tmdb_id = note.get_tmdb_id()
    tmdb_type = note.get_tmdb_type()
    needs_tmdb_id = not tmdb_id or not tmdb_type

    return needs_cover, needs_metadata, needs_tmdb_id


def _fetch_required_data(
    fetcher: TMDBCoverFetcher,
    note: ObsidianNoteUpdater,
    title: str,
    needs_cover: bool,
    needs_metadata: bool,
    needs_tmdb_id: bool,
    force: bool = False,
) -> tuple[Optional[str], Dict[str, Any]]:
    """Fetch cover URL and/or metadata based on needs"""
    image_url = None
    metadata: Dict[str, Any] = {}

    # Check if we have stored TMDB ID for faster direct lookup
    tmdb_id = note.get_tmdb_id()
    tmdb_type = note.get_tmdb_type()

    if tmdb_id and tmdb_type and not force:
        # We have TMDB ID, use direct lookup (unless force flag is set)
        print(f"  Using stored TMDB ID: {tmdb_id} ({tmdb_type})")

        # If we only need the TMDB ID and already have it, we're done
        if not needs_cover and not needs_metadata and not needs_tmdb_id:
            return None, {}

        if needs_cover and needs_metadata:
            if note.has_external_cover():
                image_url = note.get_existing_cover_url()
                print("  Found external cover URL, will download locally")
                _, metadata = fetcher.get_cover_and_metadata_by_id(tmdb_id, tmdb_type)
            else:
                image_url, metadata = fetcher.get_cover_and_metadata_by_id(
                    tmdb_id, tmdb_type
                )
        elif needs_cover:
            if note.has_external_cover():
                image_url = note.get_existing_cover_url()
                print("  Found external cover URL, will download locally")
            else:
                image_url = fetcher.get_cover_url_by_id(tmdb_id, tmdb_type)
            # Also get metadata to ensure we have the TMDB ID
            metadata = fetcher.get_metadata_by_id(tmdb_id, tmdb_type)
        elif needs_metadata:
            print("  Fetching metadata only...")
            metadata = fetcher.get_metadata_by_id(tmdb_id, tmdb_type)
    else:
        # No stored ID (or force flag set), search by title with interactive selection
        if force and tmdb_id and tmdb_type:
            print(f"  Force mode: ignoring stored TMDB ID {tmdb_id} ({tmdb_type})")

        # Get up to 10 results to show user
        results = fetcher.search_multi(title, limit=10)

        if not results:
            print("  No results found")
            return None, {}

        # If only one result, use it automatically
        selected_result: Optional[Dict[str, Any]]
        if len(results) == 1:
            selected_result = results[0]
            media_type = (
                "movie" if selected_result.get("media_type") == "movie" else "TV show"
            )
            name = selected_result.get("title") or selected_result.get(
                "name", "Unknown"
            )
            print(f"  Found {media_type}: {name}")
        else:
            # Show interactive selector
            print(f"  Found {len(results)} results, showing selector...")
            selected_result = select_tmdb_result(title, results)

            if not selected_result:
                print("  Selection skipped by user")
                return None, {}

            media_type = (
                "movie" if selected_result.get("media_type") == "movie" else "TV show"
            )
            name = selected_result.get("title") or selected_result.get(
                "name", "Unknown"
            )
            print(f"  Selected {media_type}: {name}")

        # Now fetch cover and/or metadata based on the selected result
        if not selected_result.get("poster_path"):
            print("  Selected result has no poster")
            return None, {}

        cover_url = f"{fetcher.image_base_url}{selected_result['poster_path']}"
        metadata = fetcher.get_metadata(selected_result)

        # Handle different scenarios
        if needs_cover and needs_metadata:
            if note.has_external_cover():
                image_url = note.get_existing_cover_url()
                print("  Found external cover URL, will download locally")
            else:
                image_url = cover_url
        elif needs_cover:
            if note.has_external_cover():
                image_url = note.get_existing_cover_url()
                print("  Found external cover URL, will download locally")
            else:
                image_url = cover_url
        elif needs_metadata or needs_tmdb_id:
            # Just metadata, no cover needed
            pass

    return image_url, metadata


def main() -> None:
    """Process all markdown files in a directory"""
    parser = argparse.ArgumentParser(
        description="Add TMDB cover images to Obsidian notes"
    )
    parser.add_argument(
        "directory", help="Path to Obsidian vault or folder containing markdown files"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-search even if TMDB ID is already stored (useful for fixing wrong data)",
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
            needs_cover, needs_metadata, needs_tmdb_id = _determine_processing_needs(
                note
            )

            # Skip only if we don't need anything at all (unless force flag is set)
            if (
                not needs_cover
                and not needs_metadata
                and not needs_tmdb_id
                and not args.force
            ):
                print("  Already has cover, metadata, and TMDB ID, skipping...")
                skipped += 1
                continue

            # Fetch required data
            image_url, metadata = _fetch_required_data(
                tmdb,
                note,
                title,
                needs_cover,
                needs_metadata,
                needs_tmdb_id,
                args.force,
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
