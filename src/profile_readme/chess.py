"""Chess.com rating chart generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
)
ARCHIVES_URL = "https://api.chess.com/pub/player/{user}/games/archives"


@dataclass(frozen=True)
class ChessConfig:
    username: str = "itsashelf"
    time_class: str = "rapid"
    rules: str = "chess"
    game_count: int = 100
    chart_height: int = 15


def _get_json(url: str) -> dict[str, Any]:
    import requests

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def get_archives(config: ChessConfig = ChessConfig()) -> list[str]:
    """Fetch monthly archive URLs newest-first."""
    try:
        archives = _get_json(ARCHIVES_URL.format(user=config.username)).get("archives", [])
    except Exception as error:
        LOGGER.error("Error fetching chess archives: %s", error)
        return []

    return list(reversed(archives))


def get_filtered_games(monthly_archive_url: str, config: ChessConfig) -> list[dict[str, Any]]:
    """Fetch games from one monthly archive and keep the configured variant."""
    try:
        games = _get_json(monthly_archive_url).get("games", [])
    except Exception as error:
        LOGGER.error("Error fetching chess games from %s: %s", monthly_archive_url, error)
        return []

    filtered = [
        game
        for game in games
        if game.get("time_class") == config.time_class and game.get("rules") == config.rules
    ]
    return list(reversed(filtered))


def ratings_from_games(games: list[dict[str, Any]], username: str) -> list[int]:
    """Extract the configured player's rating from each game."""
    ratings = []
    lowered_username = username.lower()

    for game in games:
        white = game.get("white", {})
        black = game.get("black", {})
        if not isinstance(white, dict) or not isinstance(black, dict):
            continue

        player = white if white.get("username", "").lower() == lowered_username else black
        rating = player.get("rating")
        if isinstance(rating, int):
            ratings.append(rating)

    return list(reversed(ratings))


def generate_rating_chart(config: ChessConfig = ChessConfig()) -> str | None:
    """Generate an ASCII rating chart for recent Chess.com games."""
    import asciichartpy as asciichart

    games: list[dict[str, Any]] = []
    for archive in get_archives(config):
        games.extend(get_filtered_games(archive, config))
        if len(games) >= config.game_count:
            break

    ratings = ratings_from_games(games[: config.game_count], config.username)
    if not ratings or min(ratings) == max(ratings):
        return None

    return asciichart.plot(
        ratings,
        {"height": config.chart_height, "min": min(ratings), "max": max(ratings)},
    )
