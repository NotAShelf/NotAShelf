"""Tarot spread, fortune, and project-card SVG rendering."""

from __future__ import annotations

import html
import hashlib
import textwrap
from typing import NamedTuple

from profile_readme.models import ProjectCard
from profile_readme.paths import TEMPLATES
from profile_readme.svg import DEFAULT_THEME, Theme
from profile_readme.templates import render_template

TAROT_ICON_DIR = TEMPLATES / "tarot-icons"


class TarotCard(NamedTuple):
    numeral: str
    title: str
    symbol: str


class TarotDraw(NamedTuple):
    project_card: ProjectCard
    card: TarotCard
    reversed: bool


TAROT_DECK = (
    TarotCard("0", "The First Commit", "first-commit"),
    TarotCard("I", "The Toolsmith", "toolsmith"),
    TarotCard("II", "The Hidden State", "hidden-state"),
    TarotCard("III", "The Module Grove", "module-grove"),
    TarotCard("IV", "The System Root", "system-root"),
    TarotCard("V", "The Convention", "convention"),
    TarotCard("VI", "The Linker", "linker"),
    TarotCard("VII", "The Runner", "runner"),
    TarotCard("VIII", "The Steady Hand", "steady-hand"),
    TarotCard("IX", "The Inspector", "inspector"),
    TarotCard("X", "The Scheduler", "scheduler"),
    TarotCard("XI", "The Gatekeeper", "gatekeeper"),
    TarotCard("XII", "The Inversion", "inversion"),
    TarotCard("XIII", "The Pruner", "pruner"),
    TarotCard("XIV", "The Compositor", "compositor"),
    TarotCard("XV", "The Vendor", "vendor"),
    TarotCard("XVI", "The Breakage", "breakage"),
    TarotCard("XVII", "The Declarative Star", "declarative-star"),
    TarotCard("XVIII", "The Mirage", "mirage"),
    TarotCard("XIX", "The Beacon", "beacon"),
    TarotCard("XX", "The Release Bell", "release-bell"),
    TarotCard("XXI", "The Closure", "closure"),
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
    if len(draws) != 3:
        raise ValueError("A project spotlight reading needs exactly three cards")

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


def _svg_text_lines(text: str, *, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) <= max_lines:
        return lines

    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1].rstrip(".") + "..."
    return clipped


def _project_title_size(title: str) -> int:
    available_width = 228
    estimated = int(available_width / max(len(title), 1) / 0.62)
    return max(16, min(32, estimated))


def _load_icon(symbol: str) -> str:
    icon_path = TAROT_ICON_DIR / f"{symbol}.svg"
    if not icon_path.exists():
        raise ValueError(f"Missing tarot icon template: {icon_path}")

    return icon_path.read_text(encoding="utf-8").strip()


def validate_tarot_deck() -> None:
    """Validate deck uniqueness and icon coverage."""
    fields = {
        "title": [card.title for card in TAROT_DECK],
        "symbol": [card.symbol for card in TAROT_DECK],
        "numeral": [card.numeral for card in TAROT_DECK],
    }
    for field, values in fields.items():
        if len(values) != len(set(values)):
            raise ValueError(f"Tarot deck contains duplicate {field} values")

    for card in TAROT_DECK:
        _load_icon(card.symbol)


def _render_scene(card: TarotCard, *, cx: float, cy: float) -> str:
    icon = _load_icon(card.symbol)
    return f"""
<circle class="halo-ring" cx="{cx:g}" cy="{cy:g}" r="76"/>
<circle class="seal" cx="{cx:g}" cy="{cy:g}" r="62"/>
<path class="emblem-thin" d="M{cx - 72:g} {cy + 82:g} H{cx + 72:g}"/>
<g transform="translate({cx - 80:g} {cy - 80:g})">
{icon}
</g>
"""


def _edge_decorations(width: int, height: int) -> str:
    cx = width / 2
    return f"""
<g class="ornament">
  <path d="M55 76 L69 76 M55 76 L55 90 M{width - 55:g} 76 L{width - 69:g} 76 M{width - 55:g} 76 L{width - 55:g} 90"/>
  <path d="M53 {height - 53:g} L65 {height - 53:g} M53 {height - 53:g} L53 {height - 65:g} M{width - 53:g} {height - 53:g} L{width - 65:g} {height - 53:g} M{width - 53:g} {height - 53:g} L{width - 53:g} {height - 65:g}"/>
  <path d="M{cx - 22:g} 120 L{cx:g} 108 L{cx + 22:g} 120 L{cx:g} 132 Z"/>
  <path d="M61 105 C74 98 88 98 101 105 M{width - 61:g} 105 C{width - 74:g} 98 {width - 88:g} 98 {width - 101:g} 105"/>
  <path d="M{cx - 34:g} {height - 75:g} L{cx:g} {height - 96:g} L{cx + 34:g} {height - 75:g} L{cx:g} {height - 54:g} Z"/>
  <path d="M{cx - 105:g} {height - 73:g} L{cx - 84:g} {height - 86:g} L{cx - 63:g} {height - 73:g} L{cx - 84:g} {height - 60:g} Z"/>
  <path d="M{cx + 63:g} {height - 73:g} L{cx + 84:g} {height - 86:g} L{cx + 105:g} {height - 73:g} L{cx + 84:g} {height - 60:g} Z"/>
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
    draw: TarotDraw,
    *,
    theme: Theme = DEFAULT_THEME,
    width: int = 330,
    height: int = 520,
) -> str:
    """Render one tarot draw as a project-card SVG."""
    _ = theme
    category, project = draw.project_card
    arcana = html.escape(draw.card.title)
    numeral = html.escape(draw.card.numeral)
    title = html.escape(project["title"])
    orientation = "reversed" if draw.reversed else "upright"
    suit = html.escape(f"{category.split(',')[0]} / {orientation}")
    description_lines = [
        html.escape(line) for line in _svg_text_lines(project["description"], width=30, max_lines=4)
    ]

    desc = "\n".join(
        f'<text x="{width / 2:g}" y="{358 + index * 20}" class="body" text-anchor="middle">{line}</text>'
        for index, line in enumerate(description_lines)
    )
    scene = _render_scene(draw.card, cx=width / 2, cy=178)

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
            "PROJECT_TITLE_SIZE": _project_title_size(project["title"]),
            "SUIT": suit,
            "DESCRIPTION": desc,
        },
    )
