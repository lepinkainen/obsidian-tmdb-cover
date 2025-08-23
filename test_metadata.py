#!/usr/bin/env python3
"""
Basic tests for the new metadata functionality
"""

import tempfile
import os
import sys

# Add the current directory to Python path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the classes from the script
import importlib.util

spec = importlib.util.spec_from_file_location("obsidian_cover", "obsidian-cover.py")
obsidian_cover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obsidian_cover)

TMDBCoverFetcher = obsidian_cover.TMDBCoverFetcher
ObsidianNoteUpdater = obsidian_cover.ObsidianNoteUpdater


def test_note_updater_metadata():
    """Test ObsidianNoteUpdater metadata methods"""
    print("Testing ObsidianNoteUpdater metadata functionality...")

    # Create a temporary markdown file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
title: Test Movie
tags: ["existing-tag"]
---

# Test Movie

Some content here.
""")
        temp_file = f.name

    try:
        # Test metadata updates
        note = ObsidianNoteUpdater(temp_file)

        # Test runtime update
        assert note.update_runtime(120)
        assert note.frontmatter["runtime"] == 120
        print("✓ Runtime update works")

        # Test tag update
        new_tags = ["movie/Action", "movie/Adventure"]
        assert note.update_tags(new_tags)
        expected_tags = ["existing-tag", "movie/Action", "movie/Adventure"]
        assert set(note.frontmatter["tags"]) == set(expected_tags)
        print("✓ Tag merging works")

        # Test metadata update
        metadata = {"runtime": 150, "genre_tags": ["movie/Comedy", "movie/Drama"]}
        assert note.update_metadata(metadata)
        assert note.frontmatter["runtime"] == 150
        expected_final_tags = [
            "existing-tag",
            "movie/Action",
            "movie/Adventure",
            "movie/Comedy",
            "movie/Drama",
        ]
        assert set(note.frontmatter["tags"]) == set(expected_final_tags)
        print("✓ Metadata update works")

        print("All ObsidianNoteUpdater tests passed!")

    finally:
        # Clean up
        os.unlink(temp_file)


def test_tmdb_fetcher():
    """Test TMDBCoverFetcher functionality (requires API key)"""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("Skipping TMDB tests - no API key set")
        return

    print("Testing TMDBCoverFetcher functionality...")

    fetcher = TMDBCoverFetcher(api_key)

    # Test genre caching
    movie_genres = fetcher._get_genres("movie")
    tv_genres = fetcher._get_genres("tv")

    assert len(movie_genres) > 0, "Should fetch movie genres"
    assert len(tv_genres) > 0, "Should fetch TV genres"
    print("✓ Genre fetching works")

    # Test metadata extraction for a well-known movie
    cover_url, metadata = fetcher.get_cover_and_metadata("The Matrix")

    if cover_url and metadata:
        print(f"✓ Found cover for The Matrix: {cover_url[:50]}...")
        if "runtime" in metadata:
            print(f"✓ Runtime: {metadata['runtime']} minutes")
        if "genre_tags" in metadata:
            print(f"✓ Genres: {', '.join(metadata['genre_tags'])}")
    else:
        print("⚠ Could not fetch The Matrix data (might be rate limited)")

    print("TMDB tests completed!")


def test_genre_sanitization():
    """Test genre name sanitization"""
    print("Testing genre name sanitization...")

    api_key = "dummy_key"  # We don't need a real key for this test
    fetcher = TMDBCoverFetcher(api_key)

    # Test various problematic genre names
    test_cases = [
        ("Sci-Fi & Fantasy", "Sci-Fi-and-Fantasy"),
        ("Action & Adventure", "Action-and-Adventure"),
        ("Comedy/Drama", "Comedy-Drama"),
        ("Horror#Thriller", "HorrorThriller"),
        ("  Documentary  ", "Documentary"),
        ("Science Fiction", "Science-Fiction"),
        ("War & Politics", "War-and-Politics"),
    ]

    for input_name, expected in test_cases:
        result = fetcher._sanitize_genre_name(input_name)
        assert result == expected, (
            f"Expected '{expected}' but got '{result}' for input '{input_name}'"
        )
        print(f"✓ '{input_name}' → '{result}'")

    print("Genre sanitization tests passed!")


if __name__ == "__main__":
    print("Running basic metadata functionality tests...\n")

    test_note_updater_metadata()
    print()
    test_genre_sanitization()
    print()
    test_tmdb_fetcher()

    print("\nTests completed!")
