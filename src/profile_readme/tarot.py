"""Tarot spread, fortune, and project-card SVG rendering."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import textwrap
from functools import cache
from typing import NamedTuple

from profile_readme.models import ProjectCard
from profile_readme.paths import TEMPLATES
from profile_readme.templates import render_template

TAROT_ART_DIR = TEMPLATES / "tarot-art"


class TarotCard(NamedTuple):
    numeral: str
    title: str
    symbol: str


class TarotDraw(NamedTuple):
    project_card: ProjectCard
    card: TarotCard
    reversed: bool


TAROT_DECK = (
    TarotCard("0", "The Fool", "first-commit"),
    TarotCard("I", "The Magician", "toolsmith"),
    TarotCard("II", "The High Priestess", "hidden-state"),
    TarotCard("III", "The Empress", "module-grove"),
    TarotCard("IV", "The Emperor", "system-root"),
    TarotCard("V", "The Hierophant", "convention"),
    TarotCard("VI", "The Lovers", "linker"),
    TarotCard("VII", "The Chariot", "runner"),
    TarotCard("VIII", "Strength", "steady-hand"),
    TarotCard("IX", "The Hermit", "inspector"),
    TarotCard("X", "Wheel of Fortune", "scheduler"),
    TarotCard("XI", "Justice", "gatekeeper"),
    TarotCard("XII", "The Hanged Man", "inversion"),
    TarotCard("XIII", "Death", "pruner"),
    TarotCard("XIV", "Temperance", "compositor"),
    TarotCard("XV", "The Devil", "vendor"),
    TarotCard("XVI", "The Tower", "breakage"),
    TarotCard("XVII", "The Star", "declarative-star"),
    TarotCard("XVIII", "The Moon", "mirage"),
    TarotCard("XIX", "The Sun", "beacon"),
    TarotCard("XX", "Judgement", "release-bell"),
    TarotCard("XXI", "The World", "closure"),
)


def _stable_number(*parts: object) -> int:
    payload = "\0".join(str(part) for part in parts).encode()
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big")


def draw_tarot_spread(cards: list[ProjectCard], *, seed: str | None = None) -> list[TarotDraw]:
    """Assign selected projects to unique Major Arcana cards."""
    used: set[int] = set()
    draws = []

    for index, project_card in enumerate(cards):
        category, project = project_card
        base = _stable_number(seed or "", index, category, project["title"], project["link"])
        card_index = base % len(TAROT_DECK)
        while card_index in used:
            card_index = (card_index + 1) % len(TAROT_DECK)

        used.add(card_index)
        reversed_card = bool(
            _stable_number("orientation", seed or "", category, project["title"], project["link"])
            % 2
        )
        draws.append(TarotDraw(project_card, TAROT_DECK[card_index], reversed_card))

    return draws


def render_fortune(draws: list[TarotDraw]) -> str:
    """Render one project-centered reading for the selected spotlight cards."""

    def entry(draw: TarotDraw) -> dict[str, str]:
        _category, project = draw.project_card
        description = project["description"].rstrip(".")
        return {
            "project": project["title"],
            "card": draw.card.title,
            "orientation": "reversed" if draw.reversed else "upright",
            "description": description[:1].lower() + description[1:],
        }

    root, crossing, path = [entry(draw) for draw in draws]
    combination = " / ".join(
        f"{entry['card']} ({entry['orientation']})" for entry in (root, crossing, path)
    )

    reading = (
        f"Spread: <em>{html.escape(combination)}</em>.<br>"
        f"Root: <strong>{html.escape(root['project'])}</strong> draws "
        f"<em>{html.escape(root['card'])}</em> ({root['orientation']}), grounding the spread in "
        f"{html.escape(root['description'])}. "
        f"Crossing: <strong>{html.escape(crossing['project'])}</strong> draws "
        f"<em>{html.escape(crossing['card'])}</em> ({crossing['orientation']}), putting pressure on "
        f"{html.escape(crossing['description'])}. "
        f"Path: <strong>{html.escape(path['project'])}</strong> draws "
        f"<em>{html.escape(path['card'])}</em> ({path['orientation']}), turning the reading toward "
        f"{html.escape(path['description'])}."
    )
    return "\n".join(
        [
            '<details align="center">',
            "<summary><strong>Fortune</strong></summary>",
            "",
            f'<p align="center">{reading}</p>',
            "</details>",
        ]
    )


def _project_title_size(title: str) -> int:
    return max(17, min(25, int(250 / max(len(title), 1) / 0.56)))


@cache
def _scan_catalog() -> dict:
    return json.loads((TAROT_ART_DIR / "manifest.json").read_text(encoding="utf-8"))


@cache
def _scan_data(name: str) -> str:
    return base64.b64encode((TAROT_ART_DIR / f"{name}.jpg").read_bytes()).decode("ascii")


def _render_scene(draw: TarotDraw) -> str:
    catalog = _scan_catalog()
    name = catalog["cards"][draw.card.symbol]
    plate = catalog["plates"][name]
    credit = html.escape(
        f"Gustave Doré, Inferno (1861), {plate['title']}. "
        f"{catalog['catalog']}; scan leaf {plate['scan_leaf']}. {catalog['rights']}"
    )
    return (
        f"<g><desc>{credit}</desc>"
        '<image x="37" y="75" width="256" height="278" '
        'preserveAspectRatio="xMidYMid slice" '
        f'href="data:image/jpeg;base64,{_scan_data(name)}"/>'
        '<rect x="37" y="75" width="256" height="278" fill="none" '
        'stroke="var(--rule, #9f9987)" stroke-width="0.8"/></g>'
    )


@cache
def _engraved_frame() -> str:
    """Keep engraved corner flourishes outside the illustration and lettering."""
    corner = (
        '<path d="M0 32 V8 Q0 0 8 0 H25 M3 28 V9 Q3 3 9 3 H22 '
        "M0 17 C12 14 13 5 7 6 C1 7 4 14 9 10 "
        'M7 22 C13 18 15 11 12 8 M4 28 C10 26 15 23 17 17"/>'
        '<path d="M7 22 C7 16 2 15 1 18 C0 21 5 23 7 22 '
        'M12 16 C18 15 19 10 16 10 C13 10 11 13 12 16"/>'
    )
    return "".join(
        f'<g class="scrollwork" transform="translate({x} {y}) scale({sx} {sy})">{corner}</g>'
        for x, y, sx, sy in ((23, 23, 1, 1), (307, 23, -1, 1), (23, 537, 1, -1), (307, 537, -1, -1))
    )


def render_project_card_svg(
    draw: TarotDraw,
    *,
    width: int = 330,
    height: int = 560,
) -> str:
    """Render one tarot draw as a project-card SVG."""
    category, project = draw.project_card
    title = html.escape(project["title"])
    orientation = "reversed" if draw.reversed else "upright"
    category_label = "Software" if "," in category else category
    description_lines = textwrap.wrap(project["description"], width=35)
    # Fit the full description between the category and the bottom ornament.
    line_height = min(18, 54 / max(len(description_lines) - 1, 1))
    body_size = min(15, line_height - 1)
    desc = "\n".join(
        f'<text x="165" y="{480 + index * line_height:g}" class="body" '
        f'font-size="{body_size:g}" text-anchor="middle">{html.escape(line)}</text>'
        for index, line in enumerate(description_lines)
    )
    scene = _render_scene(draw)

    return render_template(
        TEMPLATES / "project-card.svg",
        {
            "WIDTH": width,
            "HEIGHT": height,
            "TITLE": title,
            "ACCESSIBLE_DESCRIPTION": html.escape(
                f"{draw.card.numeral}. {draw.card.title}, {orientation}. "
                f"{category_label}. {project['description']}"
            ),
            "NUMERAL": html.escape(draw.card.numeral),
            "ARCANA": html.escape(draw.card.title),
            "SCENE": scene,
            "ORNAMENTS": _engraved_frame(),
            "PROJECT_TITLE": title,
            "PROJECT_TITLE_SIZE": _project_title_size(project["title"]),
            "SUIT": html.escape(f"{category_label} / {orientation}"),
            "DESCRIPTION": desc,
        },
    )
