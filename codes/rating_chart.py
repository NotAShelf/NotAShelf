import os
import logging
from collections import namedtuple
import datetime
import math
import asciichartpy as ac
import requests

# Configure logging based on DEBUG environment variable
if os.environ.get("DEBUG") == "True":
    logging.basicConfig(
        level=logging.DEBUG,  # Set the logging level to DEBUG for maximum detail
        format="%(asctime)s [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        level=logging.INFO,  # Set the logging level to INFO for less verbose output
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
        headers = {
            "User-Agent": FAKE_USER_AGENT
        }  # Set the fake user agent in the request headers
        response = requests.get(ARCHIVES_URL.format(user=USERNAME), headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

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
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {e}")
        return []


# Define get_filtered_games and other functions as before


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
        return ac.plot(ratings_list, {"height": 15})
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
