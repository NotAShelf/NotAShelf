import logging
from collections import namedtuple
import datetime
import math
import os
import sys
import asciichartpy as ac
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG for maximum detail
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

USERNAME = "itsashelf"
TIME_CLASS = "rapid"
RULES = "chess"  # chess960 and other variants possible here
NGAMES = 100
ARCHIVES_URL = "https://api.chess.com/pub/player/{user}/games/archives"

# Define a fake user agent
FAKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"


def get_archives() -> list:
    try:
        logging.info("Fetching game archives...")
        headers = {"User-Agent": FAKE_USER_AGENT}
        response = requests.get(ARCHIVES_URL.format(user=USERNAME), headers=headers, timeout=10)
        response.raise_for_status()
        archives_dict = response.json()
        monthly_archives = archives_dict.get("archives")
        if monthly_archives is None:
            logging.info("No game archives found.")
            return []
        logging.info(f"Game archives retrieved successfully: {monthly_archives}")
        return monthly_archives[::-1]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching archives: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in get_archives: {e}")
        return []


def get_filtered_games(monthly_archive_url: str) -> list:
    try:
        logging.info(f"Fetching games from {monthly_archive_url}...")
        headers = {"User-Agent": FAKE_USER_AGENT}
        response = requests.get(monthly_archive_url, headers=headers, timeout=10)
        response.raise_for_status()
        games_dict = response.json()
        monthly_games = games_dict.get("games")
        if monthly_games is None:
            logging.info("No games found in this archive.")
            return []
        _filtered_games = [g for g in monthly_games if g.get("time_class") == TIME_CLASS]
        filtered_games = [g for g in _filtered_games if g.get("rules") == RULES]
        logging.info(f"Games retrieved successfully from {monthly_archive_url}.")
        return filtered_games[::-1]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching games: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in get_filtered_games: {e}")
        return []


def get_ratings_from_games(games: list) -> list:
    ratings = []
    for game in games:
        try:
            if "white" in game and "black" in game and "username" in game["white"] and "username" in game["black"]:
                if game["white"]["username"].lower() == USERNAME.lower():
                    ratings.append(game["white"].get("rating", 0))
                else:
                    ratings.append(game["black"].get("rating", 0))
            else:
                ratings.append(0)
        except Exception as e:
            logging.warning(f"Malformed game data: {e}")
            ratings.append(0)
    return ratings[::-1]


def main():
    try:
        final_games = []
        archives = get_archives()
        if not archives:
            logging.info("No archives to retrieve games from.")
            return None
        for archive in archives:
            games = get_filtered_games(archive)
            if games:
                final_games += games
            if len(final_games) >= NGAMES:
                break
        final_games = final_games[:NGAMES]
        ratings_list = get_ratings_from_games(final_games)
        if not ratings_list or all(r == 0 for r in ratings_list):
            logging.info("No valid ratings data to plot.")
            return None
        min_rating = min(ratings_list)
        max_rating = max(ratings_list)
        if min_rating == max_rating:
            logging.info("Ratings are constant, chart would be flat.")
            return None
        return ac.plot(ratings_list, {"height": 15, "min": min_rating, "max": max_rating})
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    plot = main()
    if plot:
        print("Rating Chart:")
        print(plot)
    else:
        logging.info("No data available or an error occurred.")
