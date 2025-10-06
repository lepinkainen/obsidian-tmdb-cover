"""Build markdown content sections from TMDB data."""

from typing import Dict, Any, List, Optional


def _get_country_flag(country_code: str) -> str:
    """Convert ISO country code to flag emoji"""
    # Map common country codes to flag emojis
    flags = {
        "GB": "🇬🇧",
        "US": "🇺🇸",
        "CA": "🇨🇦",
        "FR": "🇫🇷",
        "DE": "🇩🇪",
        "IT": "🇮🇹",
        "ES": "🇪🇸",
        "JP": "🇯🇵",
        "KR": "🇰🇷",
        "AU": "🇦🇺",
        "NZ": "🇳🇿",
        "IN": "🇮🇳",
        "BR": "🇧🇷",
        "MX": "🇲🇽",
        "SE": "🇸🇪",
        "NO": "🇳🇴",
        "DK": "🇩🇰",
        "FI": "🇫🇮",
        "NL": "🇳🇱",
        "BE": "🇧🇪",
        "CH": "🇨🇭",
        "AT": "🇦🇹",
        "IE": "🇮🇪",
        "PL": "🇵🇱",
        "CZ": "🇨🇿",
        "RU": "🇷🇺",
        "CN": "🇨🇳",
        "TW": "🇹🇼",
        "HK": "🇭🇰",
        "SG": "🇸🇬",
        "TH": "🇹🇭",
        "ID": "🇮🇩",
        "MY": "🇲🇾",
        "PH": "🇵🇭",
        "VN": "🇻🇳",
        "AR": "🇦🇷",
        "CL": "🇨🇱",
        "CO": "🇨🇴",
        "PE": "🇵🇪",
        "ZA": "🇿🇦",
        "EG": "🇪🇬",
        "IL": "🇮🇱",
        "TR": "🇹🇷",
        "GR": "🇬🇷",
        "PT": "🇵🇹",
        "RO": "🇷🇴",
        "HU": "🇭🇺",
        "UA": "🇺🇦",
    }
    return flags.get(country_code, "🌐")


def build_overview_section(details: Dict[str, Any]) -> str:
    """Build the Overview section with synopsis and tagline"""
    overview = details.get("overview", "").strip()
    tagline = details.get("tagline", "").strip()

    if not overview:
        return ""

    section = "## Overview\n\n"
    section += f"{overview}\n"

    if tagline:
        section += f'\n> _"{tagline}"_\n'

    return section


def build_info_table(details: Dict[str, Any], media_type: str) -> str:
    """Build the Series/Movie Info table"""
    section = f"## {'Series' if media_type == 'tv' else 'Movie'} Info\n\n"
    section += "| | |\n"
    section += "|---|---|\n"

    # Status
    status = details.get("status", "Unknown")
    in_production = details.get("in_production", False)
    if media_type == "tv" and in_production:
        section += f"| **Status** | {status} (In Production) |\n"
    else:
        section += f"| **Status** | {status} |\n"

    # Seasons/Episodes for TV or Runtime for movies
    if media_type == "tv":
        seasons = details.get("number_of_seasons", 0)
        episodes = details.get("number_of_episodes", 0)
        section += f"| **Seasons** | {seasons} ({episodes} episodes) |\n"

        # Air dates for TV
        first_air = details.get("first_air_date", "")
        last_air = details.get("last_air_date", "")
        if first_air:
            air_text = first_air
            if last_air and last_air != first_air:
                air_text += f" → {last_air}"
            elif in_production:
                air_text += " → Present"
            section += f"| **Aired** | {air_text} |\n"
    else:
        # Runtime for movies
        runtime = details.get("runtime")
        if runtime:
            section += f"| **Runtime** | {runtime} min |\n"

        # Release date for movies
        release_date = details.get("release_date", "")
        if release_date:
            section += f"| **Released** | {release_date} |\n"

    # Rating
    vote_avg = details.get("vote_average", 0)
    vote_count = details.get("vote_count", 0)
    if vote_avg:
        section += f"| **Rating** | ⭐ {vote_avg:.1f}/10 ({vote_count:,} votes) |\n"

    # Network (TV) or Budget/Revenue (Movies)
    if media_type == "tv":
        networks = details.get("networks", [])
        if networks and len(networks) > 0:
            network_name = networks[0].get("name", "")
            if network_name:
                section += f"| **Network** | {network_name} |\n"
    else:
        budget = details.get("budget", 0)
        revenue = details.get("revenue", 0)
        if budget:
            section += f"| **Budget** | ${budget:,} |\n"
        if revenue:
            section += f"| **Revenue** | ${revenue:,} |\n"

    # Origin country
    origin_countries = details.get("origin_country", [])
    if origin_countries and len(origin_countries) > 0:
        country_text = " ".join(
            [f"{_get_country_flag(c)} {c}" for c in origin_countries[:3]]
        )
        section += f"| **Origin** | {country_text} |\n"

    # Content rating (for TV)
    if media_type == "tv":
        content_ratings = details.get("content_ratings", {}).get("results", [])
        us_rating = next(
            (r for r in content_ratings if r.get("iso_3166_1") == "US"), None
        )
        if us_rating:
            section += f"| **Content Rating** | {us_rating.get('rating')} |\n"

    # External IDs
    external_ids = details.get("external_ids", {})
    imdb_id = external_ids.get("imdb_id")
    tvdb_id = external_ids.get("tvdb_id")

    if imdb_id:
        section += f"| **IMDB** | [imdb.com/title/{imdb_id}](https://www.imdb.com/title/{imdb_id}/) |\n"

    if tvdb_id:
        section += f"| **TVDB** | [thetvdb.com/{tvdb_id}](https://thetvdb.com/series/{tvdb_id}) |\n"

    # Homepage
    homepage = details.get("homepage", "")
    if homepage:
        # Try to extract a friendly name from the URL
        if "apple.com" in homepage:
            link_text = "Apple TV+"
        elif "netflix.com" in homepage:
            link_text = "Netflix"
        elif "hulu.com" in homepage:
            link_text = "Hulu"
        elif "disneyplus.com" in homepage:
            link_text = "Disney+"
        elif "primevideo.com" in homepage or "amazon.com" in homepage:
            link_text = "Prime Video"
        elif "hbo.com" in homepage or "max.com" in homepage:
            link_text = "Max"
        else:
            link_text = "Official Website"
        section += f"| **Homepage** | [{link_text}]({homepage}) |\n"

    return section


def build_season_breakdown(details: Dict[str, Any]) -> str:
    """Build the Seasons section with details for each season"""
    seasons = details.get("seasons", [])

    if not seasons:
        return ""

    section = "## Seasons\n\n"

    # Show seasons in chronological order (oldest first) to avoid spoilers
    for season in seasons:
        season_number = season.get("season_number", 0)
        name = season.get("name", f"Season {season_number}")
        air_date = season.get("air_date", "")
        year = air_date[:4] if air_date else "TBA"
        vote_avg = season.get("vote_average", 0)
        overview = season.get("overview", "").strip()
        episode_count = season.get("episode_count", 0)
        poster_path = season.get("poster_path", "")

        # Season header
        section += f"### {name} ({year})"
        if vote_avg:
            section += f" • ⭐ {vote_avg:.1f}/10"
        section += "\n\n"

        # Season poster (if available)
        if poster_path:
            section += f"![{name}](https://image.tmdb.org/t/p/w300{poster_path})\n\n"

        # Overview
        if overview:
            section += f"_{overview}_\n\n"

        # Episode count and status
        section += f"**Episodes:** {episode_count}"

        # Determine if season is complete or currently airing
        # Check if this is the latest season and if show is in production
        in_production = details.get("in_production", False)
        is_latest_season = season == seasons[-1]

        if is_latest_season and in_production:
            section += " • **Status:** Currently Airing\n\n"
        else:
            section += " • **Status:** ✅ Complete\n\n"

        section += "---\n\n"

    return section.rstrip() + "\n"


def build_tmdb_content(
    details: Dict[str, Any], media_type: str, sections: Optional[List[str]] = None
) -> str:
    """
    Build complete TMDB content block from details

    Args:
        details: Full TMDB API response
        media_type: 'tv' or 'movie'
        sections: List of sections to include. Default: ['overview', 'info', 'seasons']
    """
    if sections is None:
        sections = (
            ["overview", "info", "seasons"]
            if media_type == "tv"
            else ["overview", "info"]
        )

    content_parts = []

    if "overview" in sections:
        overview_section = build_overview_section(details)
        if overview_section:
            content_parts.append(overview_section)

    if "info" in sections:
        info_section = build_info_table(details, media_type)
        if info_section:
            content_parts.append(info_section)

    if "seasons" in sections and media_type == "tv":
        season_section = build_season_breakdown(details)
        if season_section:
            content_parts.append(season_section)

    return "\n".join(content_parts)
