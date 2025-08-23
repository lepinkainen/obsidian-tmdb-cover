"""TMDB API integration for fetching movie and TV show data."""

import requests
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image  # type: ignore[import-not-found]
from io import BytesIO


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
