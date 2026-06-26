"""README rendering entry point."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from profile_readme.blog import fetch_latest_posts
from profile_readme.chess import generate_rating_chart
from profile_readme.paths import GENERATED, ROOT, TEMPLATES
from profile_readme.projects import load_projects, render_project_table, render_spotlight

BLOG_START = "<!-- Blogposts section"
BLOG_END = "<!-- End posts section -->"
CHART_START = "  ♟︎ | Chess.com Rapid Rating Chart"
CHART_END = "  Chart last updated -"
GENERATED_ASSET_URL = "https://raw.githubusercontent.com/NotAShelf/NotAShelf/output/generated"


def _replace_required(content: str, placeholder: str, replacement: str) -> str:
    if placeholder not in content:
        raise ValueError(f"Missing placeholder: {placeholder}")
    return content.replace(placeholder, replacement)


def _extract_between(content: str, start: str, end: str) -> str:
    start_index = content.index(start) + len(start)
    end_index = content.index(end, start_index)
    return content[start_index:end_index].strip()


def _offline_blog_posts(readme_path: Path) -> str:
    current = readme_path.read_text(encoding="utf-8")
    section = _extract_between(current, BLOG_START, BLOG_END)
    lines = [line for line in section.splitlines() if line.startswith("- [")]
    if not lines:
        raise ValueError(f"Could not extract existing blog posts from {readme_path}")
    return "\n".join(lines)


def _offline_rating_chart(readme_path: Path) -> str:
    current = readme_path.read_text(encoding="utf-8")
    section = _extract_between(current, CHART_START, CHART_END)
    chart = section.strip()
    if not chart:
        raise ValueError(f"Could not extract existing rating chart from {readme_path}")
    return chart


def render_readme(
    *,
    template_path: Path,
    projects_path: Path,
    output_path: Path,
    today: dt.date,
    spotlight_seed: str | None = None,
    offline_from: Path | None = None,
) -> str:
    """Render the README template into a complete README."""
    template = template_path.read_text(encoding="utf-8")
    projects = load_projects(projects_path)

    if offline_from is None:
        blog_posts = fetch_latest_posts()
        rating_chart = generate_rating_chart()
        if rating_chart is None:
            raise RuntimeError("Could not generate chess rating chart")
    else:
        blog_posts = _offline_blog_posts(offline_from)
        rating_chart = _offline_rating_chart(offline_from)

    rendered = _replace_required(template, "{{ BLOG_POSTS_PLACEHOLDER }}", blog_posts)
    rendered = _replace_required(
        rendered, "{{ TABLE_PLACEHOLDER }}", render_project_table(projects)
    )
    rendered = _replace_required(rendered, "{{ RATINGS_PLACEHOLDER }}", rating_chart)
    rendered = _replace_required(rendered, "{{ LAST_UPDATED }}", today.isoformat())
    rendered = _replace_required(
        rendered,
        "{{ PROJECT_SPOTLIGHT_PLACEHOLDER }}",
        render_spotlight(
            projects,
            seed=spotlight_seed,
            output_dir=GENERATED,
            asset_prefix=GENERATED_ASSET_URL,
        ),
    )

    output_path.write_text(rendered, encoding="utf-8")
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description="Render README.md from profile templates")
    parser.add_argument("--template", type=Path, default=TEMPLATES / "README-1.md")
    parser.add_argument("--projects", type=Path, default=TEMPLATES / "projects.json")
    parser.add_argument("--output", type=Path, default=ROOT / "README.md")
    parser.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--spotlight-seed")
    parser.add_argument(
        "--offline-from",
        type=Path,
        help="Reuse blog posts and chess chart from an existing README instead of fetching remote data",
    )
    args = parser.parse_args()

    render_readme(
        template_path=args.template,
        projects_path=args.projects,
        output_path=args.output,
        today=args.date,
        spotlight_seed=args.spotlight_seed,
        offline_from=args.offline_from,
    )


if __name__ == "__main__":
    main()
