"""Lichess rapid rating chart generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

USER_AGENT = "NotAShelf profile README asset generator"
GAMES_URL = "https://lichess.org/api/games/user/{user}"


@dataclass(frozen=True)
class ChessConfig:
    username: str = "notashelf"
    speed: str = "rapid"
    game_count: int = 100
    chart_height: int = 15


def _get_games(config: ChessConfig) -> list[dict[str, Any]]:
    import requests

    response = requests.get(
        GAMES_URL.format(user=config.username),
        headers={"Accept": "application/x-ndjson", "User-Agent": USER_AGENT},
        params={
            "max": config.game_count,
            "perfType": config.speed,
            "rated": "true",
            "pgnInJson": "true",
            "clocks": "false",
            "evals": "false",
            "opening": "false",
        },
        timeout=30,
    )
    response.raise_for_status()
    games = []
    for line in response.text.splitlines():
        if line.strip():
            game = json.loads(line)
            if isinstance(game, dict):
                games.append(game)
    return games


def ratings_from_games(games: list[dict[str, Any]], username: str) -> list[int]:
    """Extract the configured player's rating from each Lichess game."""
    ratings = []
    lowered_username = username.lower()
    for game in reversed(games):
        players = game.get("players", {})
        if not isinstance(players, dict):
            continue
        for player in players.values():
            if not isinstance(player, dict):
                continue
            user = player.get("user", {})
            if isinstance(user, dict) and user.get("name", "").lower() == lowered_username:
                rating = player.get("rating")
                if isinstance(rating, int):
                    ratings.append(rating)
                break
    return ratings


def generate_rating_chart(config: ChessConfig = ChessConfig()) -> str | None:
    """Generate an ASCII rating chart for recent Lichess rapid games."""
    import asciichartpy as asciichart

    ratings = ratings_from_games(_get_games(config), config.username)
    if not ratings or min(ratings) == max(ratings):
        return None

    return asciichart.plot(
        ratings,
        {"height": config.chart_height, "min": min(ratings), "max": max(ratings)},
    )
