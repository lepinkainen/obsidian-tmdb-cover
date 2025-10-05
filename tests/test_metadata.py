#!/usr/bin/env python3
"""
Tests for obsidian-tmdb-cover package
"""

import tempfile
import os
from pathlib import Path
import pytest

from obsidian_tmdb_cover.fetcher import TMDBCoverFetcher
from obsidian_tmdb_cover.updater import ObsidianNoteUpdater


def test_note_updater_metadata():
    """Test ObsidianNoteUpdater metadata methods"""
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

        # Test tag update
        new_tags = ["movie/Action", "movie/Adventure"]
        assert note.update_tags(new_tags)
        expected_tags = ["existing-tag", "movie/Action", "movie/Adventure"]
        assert set(note.frontmatter["tags"]) == set(expected_tags)

        # Test metadata update with TMDB ID
        metadata = {
            "runtime": 150,
            "genre_tags": ["movie/Comedy", "movie/Drama"],
            "tmdb_id": 12345,
            "tmdb_type": "movie",
        }
        assert note.update_metadata(metadata)
        assert note.frontmatter["runtime"] == 150
        assert note.frontmatter["tmdb_id"] == 12345
        assert note.frontmatter["tmdb_type"] == "movie"
        expected_final_tags = [
            "existing-tag",
            "movie/Action",
            "movie/Adventure",
            "movie/Comedy",
            "movie/Drama",
        ]
        assert set(note.frontmatter["tags"]) == set(expected_final_tags)

        # Test TMDB ID retrieval
        assert note.get_tmdb_id() == 12345
        assert note.get_tmdb_type() == "movie"

    finally:
        # Clean up
        os.unlink(temp_file)


def test_genre_sanitization():
    """Test genre name sanitization"""
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


def test_note_updater_title_extraction():
    """Test title extraction from different sources"""
    # Test frontmatter title
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
title: Frontmatter Title
---
# Heading Title
""")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        assert note.get_title() == "Frontmatter Title"
    finally:
        os.unlink(temp_file)

    # Test H1 heading title
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Heading Title\nSome content")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        assert note.get_title() == "Heading Title"
    finally:
        os.unlink(temp_file)

    # Test filename fallback
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="Filename_Title_"
    ) as f:
        f.write("Some content without title")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        title = note.get_title()
        assert "Filename_Title_" in title
    finally:
        os.unlink(temp_file)


def test_note_updater_external_cover_detection():
    """Test detection of external cover URLs"""
    # Test with external URL
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
cover: https://example.com/image.jpg
---
""")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        assert note.has_external_cover() is True
        assert note.get_existing_cover_url() == "https://example.com/image.jpg"
    finally:
        os.unlink(temp_file)

    # Test with local path
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
cover: attachments/local.jpg
---
""")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        assert note.has_external_cover() is False
        assert note.get_existing_cover_url() is None
    finally:
        os.unlink(temp_file)

    # Test with color code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
cover: "#FF5733"
---
""")
        temp_file = f.name

    try:
        note = ObsidianNoteUpdater(temp_file)
        assert note.has_external_cover() is False
        assert note._is_html_color_code("#FF5733") is True
    finally:
        os.unlink(temp_file)


def test_note_updater_cover_path_generation():
    """Test cover path generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        note_path = vault_path / "test_movie.md"
        note_path.write_text("""---
title: Test Movie 2024
---
""")

        attachments_dir = vault_path / "attachments"
        attachments_dir.mkdir()

        note = ObsidianNoteUpdater(str(note_path))
        local_path = note.generate_local_cover_path(attachments_dir)

        assert local_path.parent == attachments_dir
        assert "Test Movie 2024" in str(local_path)
        assert str(local_path).endswith(".jpg")


@pytest.mark.skipif(not os.getenv("TMDB_API_KEY"), reason="TMDB_API_KEY not set")
def test_tmdb_fetcher_with_api():
    """Test TMDBCoverFetcher functionality (requires API key)"""
    api_key = os.getenv("TMDB_API_KEY")
    fetcher = TMDBCoverFetcher(api_key)

    # Test genre caching
    movie_genres = fetcher._get_genres("movie")
    tv_genres = fetcher._get_genres("tv")

    assert len(movie_genres) > 0, "Should fetch movie genres"
    assert len(tv_genres) > 0, "Should fetch TV genres"

    # Test metadata extraction for a well-known movie
    cover_url, metadata = fetcher.get_cover_and_metadata("The Matrix")

    assert cover_url is not None, "Should find cover for The Matrix"
    assert isinstance(metadata, dict), "Should return metadata dict"

    # Test that TMDB ID is stored
    assert "tmdb_id" in metadata, "Should store TMDB ID"
    assert "tmdb_type" in metadata, "Should store TMDB type"
    assert isinstance(metadata["tmdb_id"], int), "TMDB ID should be an integer"
    assert metadata["tmdb_type"] in ["movie", "tv"], "Type should be movie or tv"

    if "runtime" in metadata:
        assert metadata["runtime"] > 0, "Runtime should be positive"

    if "genre_tags" in metadata:
        assert len(metadata["genre_tags"]) > 0, "Should have genre tags"
        assert all(
            tag.startswith("movie/") or tag.startswith("tv/")
            for tag in metadata["genre_tags"]
        ), "Genre tags should have proper prefix"


@pytest.mark.skipif(not os.getenv("TMDB_API_KEY"), reason="TMDB_API_KEY not set")
def test_tmdb_fetcher_by_id():
    """Test TMDBCoverFetcher direct ID lookup (requires API key)"""
    api_key = os.getenv("TMDB_API_KEY")
    fetcher = TMDBCoverFetcher(api_key)

    # The Matrix has TMDB ID 603 (movie)
    matrix_id = 603
    media_type = "movie"

    # Test direct metadata fetch
    metadata = fetcher.get_metadata_by_id(matrix_id, media_type)
    assert isinstance(metadata, dict), "Should return metadata dict"
    assert metadata["tmdb_id"] == matrix_id, "Should have correct TMDB ID"
    assert metadata["tmdb_type"] == media_type, "Should have correct type"

    # Test direct cover URL fetch
    cover_url = fetcher.get_cover_url_by_id(matrix_id, media_type)
    assert cover_url is not None, "Should find cover for The Matrix"
    assert "image.tmdb.org" in cover_url, "Cover URL should be from TMDB"

    # Test combined fetch
    cover_url2, metadata2 = fetcher.get_cover_and_metadata_by_id(matrix_id, media_type)
    assert cover_url2 is not None, "Should find cover"
    assert metadata2["tmdb_id"] == matrix_id, "Should have correct TMDB ID"
