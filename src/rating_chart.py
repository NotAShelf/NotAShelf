#!/usr/bin/env python3
"""Print the Chess.com rapid rating chart."""

from __future__ import annotations

import logging

from profile_readme.chess import generate_rating_chart


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
    chart = generate_rating_chart()
    if chart is None:
        raise SystemExit("No chess rating data available")

    print("Rating Chart:")
    print(chart)


if __name__ == "__main__":
    main()
