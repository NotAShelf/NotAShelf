"""Project catalog loading and README section rendering."""

from __future__ import annotations

import html
import json
import random
import textwrap
from pathlib import Path
from typing import NamedTuple, TypedDict

from profile_readme.paths import TEMPLATES
from profile_readme.svg import DEFAULT_THEME, Theme
from profile_readme.templates import render_template


class ProjectItem(TypedDict):
    title: str
    link: str
    description: str


class ProjectCard(NamedTuple):
    category: str
    project: ProjectItem


ProjectCatalog = dict[str, list[ProjectItem]]

TABLE_COLUMNS = ("Nix", "Go, Rust, Python, JavaScript, TypeScript")
CENTERED_TABLES = ("Neovim Plugins",)
TAROT_TITLES = {
    "Nix": "The Declarative Star",
    "Go, Rust, Python, JavaScript, TypeScript": "The Toolsmith",
    "Neovim Plugins": "The Editor",
}
TAROT_NUMERALS = {
    "Nix": "XVII",
    "Go, Rust, Python, JavaScript, TypeScript": "I",
    "Neovim Plugins": "IX",
}
TAROT_MEANINGS = {
    "Nix": {
        "card": "The Declarative Star",
        "upright": "structure, repeatability, and a system that becomes clearer once its inputs are named",
        "advice": "trust the shape of the system before adding another moving part",
    },
    "Go, Rust, Python, JavaScript, TypeScript": {
        "card": "The Toolsmith",
        "upright": "craft, leverage, and the useful constraint of choosing one sharp instrument",
        "advice": "make the next tool smaller, sharper, and easier to carry",
    },
    "Neovim Plugins": {
        "card": "The Editor",
        "upright": "attention, refinement, and the command that appears after the noise is trimmed",
        "advice": "cut the distraction first; the next edit is already visible",
    },
}


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
    cells = []

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    for index, (category, project) in enumerate(cards, start=1):
        title = html.escape(project["title"])
        link = html.escape(project["link"], quote=True)
        filename = f"project-spotlight-{index}.svg"
        if output_dir is not None:
            (output_dir / filename).write_text(
                render_project_card_svg(ProjectCard(category, project)),
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
            render_fortune(cards),
        ]
    )


def render_fortune(cards: list[ProjectCard]) -> str:
    """Render one reading that depends on the three selected cards."""
    if len(cards) != 3:
        raise ValueError("A project spotlight reading needs exactly three cards")

    spread = ("Root", "Tension", "Path")
    entries = []
    for position, (category, project) in zip(spread, cards):
        meaning = TAROT_MEANINGS.get(
            category,
            {
                "card": "The Side Quest",
                "upright": "a useful detour and an unfinished map",
                "advice": "follow the thread far enough to learn why it appeared",
            },
        )
        entries.append(
            {
                "position": position,
                "project": project["title"],
                "card": meaning["card"],
                "upright": meaning["upright"],
                "advice": meaning["advice"],
            }
        )

    reading = (
        f"{entries[0]['position']}: <strong>{html.escape(entries[0]['project'])}</strong> "
        f"draws <em>{html.escape(entries[0]['card'])}</em>, pointing to "
        f"{html.escape(entries[0]['upright'])}. "
        f"{entries[1]['position']}: <strong>{html.escape(entries[1]['project'])}</strong> "
        f"draws <em>{html.escape(entries[1]['card'])}</em>, testing that with "
        f"{html.escape(entries[1]['upright'])}. "
        f"{entries[2]['position']}: <strong>{html.escape(entries[2]['project'])}</strong> "
        f"draws <em>{html.escape(entries[2]['card'])}</em>; "
        f"{html.escape(entries[2]['advice'])}."
    )
    return f'<p align="center"><em>Fortune:</em><br>{reading}</p>'


def _svg_text_lines(text: str, *, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) <= max_lines:
        return lines

    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1].rstrip(".") + "..."
    return clipped


def _render_scene(category: str, *, cx: float, cy: float) -> str:
    if category == "Nix":
        return f"""
<circle class="halo-ring" cx="{cx:g}" cy="{cy:g}" r="78"/>
<path class="hill" d="M{cx - 88:g} {cy + 64:g} C{cx - 56:g} {cy + 28:g} {cx - 18:g} {cy + 28:g} {cx:g} {cy + 58:g} C{cx + 22:g} {cy + 22:g} {cx + 58:g} {cy + 30:g} {cx + 88:g} {cy + 64:g} V{cy + 84:g} H{cx - 88:g} Z"/>
<path class="water" d="M{cx - 82:g} {cy + 79:g} C{cx - 42:g} {cy + 65:g} {cx + 42:g} {cy + 92:g} {cx + 82:g} {cy + 74:g}"/>
<path class="star-fill" d="M{cx:g} {cy - 88:g} L{cx + 10:g} {cy - 53:g} L{cx + 47:g} {cy - 53:g} L{cx + 17:g} {cy - 32:g} L{cx + 29:g} {cy + 4:g} L{cx:g} {cy - 18:g} L{cx - 29:g} {cy + 4:g} L{cx - 17:g} {cy - 32:g} L{cx - 47:g} {cy - 53:g} L{cx - 10:g} {cy - 53:g} Z"/>
<circle class="moon" cx="{cx - 60:g}" cy="{cy - 45:g}" r="14"/>
<path class="card-bg" d="M{cx - 52:g} {cy - 59:g} A14 14 0 1 0 {cx - 52:g} {cy - 31:g} A9 14 0 1 1 {cx - 52:g} {cy - 59:g}"/>
<circle class="skin" cx="{cx - 28:g}" cy="{cy + 17:g}" r="10"/>
<path class="robe" d="M{cx - 44:g} {cy + 74:g} C{cx - 48:g} {cy + 47:g} {cx - 39:g} {cy + 28:g} {cx - 25:g} {cy + 27:g} C{cx - 9:g} {cy + 31:g} {cx - 7:g} {cy + 54:g} {cx - 3:g} {cy + 78:g} Z"/>
<path class="gold" d="M{cx - 18:g} {cy + 34:g} C{cx + 3:g} {cy + 30:g} {cx + 16:g} {cy + 20:g} {cx + 31:g} {cy + 7:g}"/>
<path class="green" d="M{cx - 31:g} {cy + 38:g} C{cx - 54:g} {cy + 38:g} {cx - 65:g} {cy + 52:g} {cx - 75:g} {cy + 65:g}"/>
<path class="gold thin" d="M{cx + 28:g} {cy + 9:g} C{cx + 44:g} {cy + 31:g} {cx + 51:g} {cy + 48:g} {cx + 57:g} {cy + 72:g}"/>
<path class="green thin" d="M{cx - 71:g} {cy + 66:g} C{cx - 48:g} {cy + 54:g} {cx - 28:g} {cy + 57:g} {cx - 8:g} {cy + 76:g}"/>
"""

    if category == "Neovim Plugins":
        return f"""
<circle class="halo-ring" cx="{cx:g}" cy="{cy:g}" r="75"/>
<path class="hill" d="M{cx - 82:g} {cy + 78:g} C{cx - 54:g} {cy + 46:g} {cx - 30:g} {cy + 49:g} {cx:g} {cy + 72:g} C{cx + 30:g} {cy + 49:g} {cx + 54:g} {cy + 46:g} {cx + 82:g} {cy + 78:g} Z"/>
<path class="cloak" d="M{cx - 58:g} {cy + 70:g} L{cx - 42:g} {cy - 5:g} C{cx - 29:g} {cy - 34:g} {cx + 29:g} {cy - 34:g} {cx + 42:g} {cy - 5:g} L{cx + 58:g} {cy + 70:g} Z"/>
<path class="card-bg" d="M{cx - 27:g} {cy - 12:g} C{cx - 11:g} {cy - 30:g} {cx + 11:g} {cy - 30:g} {cx + 27:g} {cy - 12:g} L{cx + 18:g} {cy + 31:g} L{cx - 18:g} {cy + 31:g} Z"/>
<path class="green" d="M{cx - 20:g} {cy + 34:g} L{cx:g} {cy - 18:g} L{cx + 20:g} {cy + 34:g} Z"/>
<path class="gold" d="M{cx - 17:g} {cy + 18:g} C{cx - 4:g} {cy + 31:g} {cx + 4:g} {cy + 31:g} {cx + 17:g} {cy + 18:g}"/>
<path class="gold" d="M{cx + 43:g} {cy - 55:g} V{cy + 44:g} M{cx + 31:g} {cy - 42:g} H{cx + 55:g} M{cx + 33:g} {cy + 33:g} H{cx + 53:g}"/>
<circle class="sun" cx="{cx + 43:g}" cy="{cy - 65:g}" r="10"/>
<path class="paper" d="M{cx - 58:g} {cy + 56:g} C{cx - 29:g} {cy + 48:g} {cx - 13:g} {cy + 54:g} {cx:g} {cy + 64:g} C{cx + 13:g} {cy + 54:g} {cx + 29:g} {cy + 48:g} {cx + 58:g} {cy + 56:g} V{cy + 72:g} C{cx + 27:g} {cy + 64:g} {cx + 12:g} {cy + 70:g} {cx:g} {cy + 80:g} C{cx - 12:g} {cy + 70:g} {cx - 27:g} {cy + 64:g} {cx - 58:g} {cy + 72:g} Z"/>
<path class="green thin" d="M{cx - 34:g} {cy + 63:g} C{cx - 17:g} {cy + 60:g} {cx - 8:g} {cy + 62:g} {cx:g} {cy + 68:g} M{cx + 34:g} {cy + 63:g} C{cx + 17:g} {cy + 60:g} {cx + 8:g} {cy + 62:g} {cx:g} {cy + 68:g}"/>
"""

    return f"""
<circle class="halo-ring" cx="{cx:g}" cy="{cy:g}" r="74"/>
<path class="hill" d="M{cx - 88:g} {cy + 78:g} C{cx - 56:g} {cy + 50:g} {cx - 28:g} {cy + 52:g} {cx:g} {cy + 73:g} C{cx + 28:g} {cy + 52:g} {cx + 56:g} {cy + 50:g} {cx + 88:g} {cy + 78:g} Z"/>
<path class="paper" d="M{cx - 78:g} {cy + 40:g} H{cx + 78:g} L{cx + 58:g} {cy + 59:g} H{cx - 58:g} Z"/>
<path class="anvil" d="M{cx - 50:g} {cy + 28:g} H{cx + 48:g} L{cx + 35:g} {cy + 44:g} H{cx - 39:g} Z"/>
<path class="gold" d="M{cx - 36:g} {cy + 25:g} C{cx - 29:g} {cy + 2:g} {cx - 17:g} {cy - 16:g} {cx + 6:g} {cy - 19:g} C{cx + 23:g} {cy - 20:g} {cx + 35:g} {cy - 9:g} {cx + 40:g} {cy + 24:g}"/>
<circle class="skin" cx="{cx + 30:g}" cy="{cy - 15:g}" r="10"/>
<path class="robe" d="M{cx - 9:g} {cy + 31:g} C{cx - 12:g} {cy + 4:g} {cx - 1:g} {cy - 10:g} {cx + 22:g} {cy - 7:g} C{cx + 42:g} {cy - 1:g} {cx + 48:g} {cy + 16:g} {cx + 55:g} {cy + 35:g}"/>
<path class="green" d="M{cx - 32:g} {cy - 14:g} C{cx - 47:g} {cy + 7:g} {cx - 39:g} {cy + 27:g} {cx - 16:g} {cy + 34:g}"/>
<path class="gold" d="M{cx + 48:g} {cy - 37:g} L{cx + 78:g} {cy - 70:g}"/>
<rect x="{cx + 69:g}" y="{cy - 82:g}" width="18" height="34" rx="2" transform="rotate(42 {cx + 78:g} {cy - 65:g})" class="hammer"/>
<path class="gold thin" d="M{cx - 17:g} {cy + 14:g} H{cx + 25:g} M{cx - 5:g} {cy + 5:g} H{cx + 33:g}"/>
<path class="spark" d="M{cx - 15:g} {cy - 26:g} L{cx - 8:g} {cy - 15:g} M{cx + 2:g} {cy - 38:g} L{cx + 2:g} {cy - 25:g} M{cx + 17:g} {cy - 30:g} L{cx + 9:g} {cy - 18:g}"/>
<path class="gold thin" d="M{cx - 68:g} {cy + 75:g} H{cx + 68:g}"/>
"""


def _edge_decorations(width: int, height: int) -> str:
    cx = width / 2
    return f"""
<g class="ornament">
  <path d="M55 76 L69 76 M55 76 L55 90 M{width - 55:g} 76 L{width - 69:g} 76 M{width - 55:g} 76 L{width - 55:g} 90"/>
  <path d="M53 {height - 53:g} L65 {height - 53:g} M53 {height - 53:g} L53 {height - 65:g} M{width - 53:g} {height - 53:g} L{width - 65:g} {height - 53:g} M{width - 53:g} {height - 53:g} L{width - 53:g} {height - 65:g}"/>
  <path d="M{cx - 24:g} 124 L{cx:g} 110 L{cx + 24:g} 124 L{cx:g} 138 Z"/>
  <path d="M61 105 C74 98 88 98 101 105 M{width - 61:g} 105 C{width - 74:g} 98 {width - 88:g} 98 {width - 101:g} 105"/>
  <path d="M{cx - 31:g} {height - 69:g} L{cx:g} {height - 88:g} L{cx + 31:g} {height - 69:g} L{cx:g} {height - 50:g} Z"/>
  <path d="M{cx - 99:g} {height - 69:g} L{cx - 82:g} {height - 80:g} L{cx - 65:g} {height - 69:g} L{cx - 82:g} {height - 58:g} Z"/>
  <path d="M{cx + 65:g} {height - 69:g} L{cx + 82:g} {height - 80:g} L{cx + 99:g} {height - 69:g} L{cx + 82:g} {height - 58:g} Z"/>
  <path d="M73 {height - 112:g} C91 {height - 101:g} 110 {height - 101:g} 128 {height - 112:g} M{width - 73:g} {height - 112:g} C{width - 91:g} {height - 101:g} {width - 110:g} {height - 101:g} {width - 128:g} {height - 112:g}"/>
  <path d="M72 {height - 82:g} H124 M206 {height - 82:g} H258 M72 {height - 56:g} H124 M206 {height - 56:g} H258"/>
  <path d="M57 198 V212 M{width - 57:g} 198 V212 M57 {height - 212:g} V{height - 198:g} M{width - 57:g} {height - 212:g} V{height - 198:g}"/>
  <circle cx="58" cy="235" r="1.7"/><circle cx="{width - 58:g}" cy="235" r="1.7"/>
  <circle cx="58" cy="{height - 235:g}" r="1.7"/><circle cx="{width - 58:g}" cy="{height - 235:g}" r="1.7"/>
</g>
<g class="wear">
  <path d="M38 84 C61 79 74 82 92 76"/>
  <path d="M236 48 C252 51 268 49 286 56"/>
  <path d="M44 {height - 139:g} C65 {height - 132:g} 89 {height - 135:g} 104 {height - 126:g}"/>
  <path d="M226 {height - 59:g} C244 {height - 66:g} 262 {height - 64:g} 286 {height - 72:g}"/>
  <circle cx="87" cy="273" r="1.3"/>
  <circle cx="244" cy="285" r="1.1"/>
  <circle cx="103" cy="{height - 92:g}" r="1.2"/>
  <circle cx="267" cy="{height - 170:g}" r="1"/>
</g>
"""


def render_project_card_svg(
    card: ProjectCard,
    *,
    theme: Theme = DEFAULT_THEME,
    width: int = 330,
    height: int = 520,
) -> str:
    """Render one project as a tarot-style SVG card."""
    category, project = card
    arcana = html.escape(TAROT_TITLES.get(category, "The Side Quest"))
    numeral = html.escape(TAROT_NUMERALS.get(category, "0"))
    title = html.escape(project["title"])
    suit = html.escape(category.split(",")[0])
    description_lines = [
        html.escape(line) for line in _svg_text_lines(project["description"], width=31, max_lines=4)
    ]

    desc = "\n".join(
        f'<text x="{width / 2:g}" y="{357 + index * 20}" class="body" text-anchor="middle">{line}</text>'
        for index, line in enumerate(description_lines)
    )
    scene = _render_scene(category, cx=width / 2, cy=178)

    return render_template(
        TEMPLATES / "project-card.svg",
        {
            "WIDTH": width,
            "HEIGHT": height,
            "TITLE": title,
            "OUTER_WIDTH": width - 20,
            "OUTER_HEIGHT": height - 20,
            "FACE_WIDTH": width - 30,
            "FACE_HEIGHT": height - 30,
            "TEXTURE_WIDTH": width - 58,
            "TEXTURE_HEIGHT": height - 58,
            "BORDER_WIDTH": width - 86,
            "BORDER_HEIGHT": height - 86,
            "CENTER_X": f"{width / 2:g}",
            "CONTENT_RIGHT": width - 72,
            "ORNAMENTS": _edge_decorations(width, height),
            "NUMERAL": numeral,
            "ARCANA": arcana,
            "SCENE": scene,
            "PROJECT_TITLE": title,
            "SUIT": suit,
            "DESCRIPTION": desc,
        },
    )
