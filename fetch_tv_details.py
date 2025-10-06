#!/usr/bin/env python3
"""Fetch comprehensive TV show details from TMDB API"""

import os
import sys
import json
import requests


def fetch_tv_show_details(tv_id: int, api_key: str):
    """Fetch all available TV show information with append_to_response"""

    # Use append_to_response to get multiple endpoints in a single call
    append_params = [
        "external_ids",  # IMDB, TVDB, etc.
        "keywords",  # Keywords/tags
        # "images",  # Posters, backdrops
        "episode_groups",  # Episode groupings
    ]

    url = f"https://api.themoviedb.org/3/tv/{tv_id}"
    params = {"api_key": api_key, "append_to_response": ",".join(append_params)}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def main():
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("Error: TMDB_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    tv_id = 95480

    print(f"Fetching all available data for TV show ID {tv_id}...\n")

    try:
        data = fetch_tv_show_details(tv_id, api_key)

        # Print formatted JSON
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print(f"Name: {data.get('name')}")
        print(f"Original Name: {data.get('original_name')}")
        print(f"First Air Date: {data.get('first_air_date')}")
        print(f"Last Air Date: {data.get('last_air_date')}")
        print(f"Status: {data.get('status')}")
        print(f"Number of Seasons: {data.get('number_of_seasons')}")
        print(f"Number of Episodes: {data.get('number_of_episodes')}")
        print(f"Vote Average: {data.get('vote_average')}")
        print(f"Genres: {', '.join(g['name'] for g in data.get('genres', []))}")

        if data.get("credits", {}).get("cast"):
            print(f"\nTop Cast ({len(data['credits']['cast'])} total):")
            for actor in data["credits"]["cast"][:5]:
                print(f"  - {actor['name']} as {actor.get('character', 'N/A')}")

        if data.get("content_ratings", {}).get("results"):
            ratings = data["content_ratings"]["results"]
            us_rating = next((r for r in ratings if r["iso_3166_1"] == "US"), None)
            if us_rating:
                print(f"\nUS Rating: {us_rating['rating']}")

        if data.get("external_ids"):
            print("\nExternal IDs:")
            ext_ids = data["external_ids"]
            if ext_ids.get("imdb_id"):
                print(f"  IMDB: {ext_ids['imdb_id']}")
            if ext_ids.get("tvdb_id"):
                print(f"  TVDB: {ext_ids['tvdb_id']}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching TV show data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
