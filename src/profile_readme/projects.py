"""Project catalog loading and README section rendering."""

from __future__ import annotations

import html
import json
import random
from pathlib import Path

from profile_readme.models import ProjectCard, ProjectCatalog, ProjectItem
from profile_readme.tarot import draw_tarot_spread, render_fortune, render_project_card_svg

TABLE_COLUMNS = ("Nix", "Go, Rust, Python, JavaScript, TypeScript")
CENTERED_TABLES = ("Neovim Plugins",)


def load_projects(path: Path) -> ProjectCatalog:
    """Load project metadata from a JSON catalog."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object keyed by project category")

    return data


def format_project_list(projects: list[ProjectItem]) -> str:
    """Format projects as a compact markdown list inside a table cell."""
    return "<br>".join(
        f"• [{project['title']}]({project['link']}) - {project['description']}"
        for project in projects
    )


def render_project_table(catalog: ProjectCatalog) -> str:
    """Render the full project catalog as the existing README markdown table."""
    left, right = TABLE_COLUMNS
    sections = [
        f"| **{left}** | **{right}** |",
        "| --- | --- |",
        f"| {format_project_list(catalog.get(left, []))} | {format_project_list(catalog.get(right, []))} |",
        "",
    ]

    for category in CENTERED_TABLES:
        sections.extend(
            [
                "<div align='center'>",
                "",
                f"| **{category}** |",
                "| --- |",
                f"| {format_project_list(catalog.get(category, []))} |",
                "</div>",
            ]
        )

    return "\n".join(sections)


def flattened_projects(catalog: ProjectCatalog) -> list[ProjectCard]:
    """Return every project with its category attached."""
    return [
        ProjectCard(category, project)
        for category, projects in catalog.items()
        for project in projects
    ]


def pick_spotlight_projects(
    catalog: ProjectCatalog,
    *,
    count: int = 3,
    seed: str | None = None,
) -> list[ProjectCard]:
    """Select random projects for the spotlight section."""
    projects = flattened_projects(catalog)
    if len(projects) < count:
        raise ValueError(f"Need at least {count} projects for the spotlight section")

    rng = random.Random(seed)
    categories = [category for category, items in catalog.items() if items]
    if len(categories) >= count:
        return [
            ProjectCard(category, rng.choice(catalog[category]))
            for category in rng.sample(categories, count)
        ]

    return rng.sample(projects, count)


def render_spotlight(
    catalog: ProjectCatalog,
    *,
    seed: str | None = None,
    output_dir: Path | None = None,
    asset_prefix: str = ".github/assets",
) -> str:
    """Render three random projects as linked tarot-card images."""
    cards = pick_spotlight_projects(catalog, seed=seed)
    draws = draw_tarot_spread(cards, seed=seed)
    cells = []

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    for index, draw in enumerate(draws, start=1):
        _category, project = draw.project_card
        title = html.escape(project["title"])
        link = html.escape(project["link"], quote=True)
        filename = f"project-spotlight-{index}.svg"
        if output_dir is not None:
            (output_dir / filename).write_text(
                render_project_card_svg(draw),
                encoding="utf-8",
            )

        cells.append(
            "\n".join(
                [
                    '<td align="center" width="33%">',
                    f'<a href="{link}">',
                    f'<img src="{asset_prefix}/{filename}" alt="{title} project card" width="220">',
                    "</a>",
                    "</td>",
                ]
            )
        )

    return "\n".join(
        [
            '<table align="center">',
            "<tr>",
            *cells,
            "</tr>",
            "</table>",
            "",
            render_fortune(draws),
        ]
    )
