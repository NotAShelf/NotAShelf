#!/usr/bin/env python3
"""Randomize the rating-chart workflow schedule."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.workflows import randomize_rating_schedule


def main() -> None:
    parser = argparse.ArgumentParser(description="Randomize the rating-chart workflow cron")
    parser.add_argument(
        "workflow",
        nargs="?",
        type=Path,
        default=Path(".github/workflows/rating-chart.yml"),
    )
    args = parser.parse_args()

    print(randomize_rating_schedule(args.workflow), end="")


if __name__ == "__main__":
    main()
