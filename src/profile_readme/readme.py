"""Update the blog list in the existing profile README."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.blog import fetch_latest_posts
from profile_readme.paths import ROOT

BLOG_START = "<!-- Blogposts section"
BLOG_END = "<!-- End posts section -->"


def replace_blog_posts(content: str, posts: str) -> str:
    """Replace only the existing blog list, retaining markers and surrounding text."""
    marker_start = content.index(BLOG_START)
    section_start = content.index("-->", marker_start) + len("-->")
    section_end = content.index(BLOG_END, section_start)
    section = content[section_start:section_end]
    existing_posts = section.strip()
    if not existing_posts or not all(
        line.startswith("- [") for line in existing_posts.splitlines()
    ):
        raise ValueError("Blog section must contain an existing markdown post list")

    list_start = section_start + len(section) - len(section.lstrip())
    list_end = section_end - (len(section) - len(section.rstrip()))
    newline = "\r\n" if "\r\n" in section else "\n"
    return content[:list_start] + posts.replace("\n", newline) + content[list_end:]


def update_readme(output_path: Path) -> str:
    """Fetch current posts without regenerating any other README content."""
    current = output_path.read_bytes().decode("utf-8")
    updated = replace_blog_posts(current, fetch_latest_posts())
    if updated != current:
        output_path.write_bytes(updated.encode("utf-8"))
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Update only the README blog list")
    parser.add_argument("--output", type=Path, default=ROOT / "README.md")
    args = parser.parse_args()
    update_readme(args.output)


if __name__ == "__main__":
    main()
