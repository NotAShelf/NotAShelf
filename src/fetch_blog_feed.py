#!/usr/bin/env python3
"""Fetch latest blog posts for README rendering."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.blog import fetch_latest_posts

PLACEHOLDER = "{{ BLOG_POSTS_PLACEHOLDER }}"


def update_readme(output_file: Path) -> None:
    """Replace the blog placeholder in a markdown file."""
    content = output_file.read_text(encoding="utf-8")
    output_file.write_text(
        content.replace(PLACEHOLDER, fetch_latest_posts()),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Update a README template with latest blog posts")
    parser.add_argument("output_file", type=Path, help="Path to the output markdown file")
    args = parser.parse_args()

    update_readme(args.output_file)


if __name__ == "__main__":
    main()
