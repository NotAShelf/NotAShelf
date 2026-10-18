"""Generate the profile's rotating SVG assets without rewriting its README."""

from __future__ import annotations

import html
import textwrap
from html.parser import HTMLParser
from pathlib import Path

from profile_readme.chess import generate_rating_chart
from profile_readme.paths import TEMPLATES
from profile_readme.projects import load_projects, pick_spotlight_projects
from profile_readme.tarot import draw_tarot_spread, render_fortune, render_project_card_svg


def render_chess_svg(chart: str) -> str:
    """Keep the ASCII plot on a fixed character grid without inter-line gaps."""
    lines = chart.splitlines()
    cell_width, cell_height = 8.5, 14
    width = max(640, max((len(line) for line in lines), default=0) * cell_width + 48)
    height = 88 + len(lines) * cell_height
    rows = "\n".join(
        f'<text x="24" y="{76 + index * cell_height}" xml:space="preserve" '
        f'textLength="{len(line) * cell_width}" lengthAdjust="spacingAndGlyphs">'
        f"{html.escape(line)}</text>"
        for index, line in enumerate(lines)
        if line
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<title>Chess.com Rapid Rating Chart</title>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" fill="#0d1117" stroke="#30363d"/>
<g fill="#c9d1d9" font-family="DejaVu Sans Mono, monospace" font-size="14">
<text x="24" y="34" fill="#f0f6fc" font-weight="bold">Chess.com Rapid Rating Chart</text>
{rows}
</g>
</svg>
'''


class _FortuneText(HTMLParser):
    """Extract the existing reading, leaving its summary to the SVG heading."""

    def __init__(self) -> None:
        super().__init__()
        self.in_paragraph = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self.in_paragraph = True
        elif tag == "br" and self.in_paragraph:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self.in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self.in_paragraph:
            self.parts.append(data)


def render_fortune_svg(reading: str) -> str:
    """Carry the complete tarot reading into a wrapped, self-contained SVG."""
    parser = _FortuneText()
    parser.feed(reading)
    paragraphs = "".join(parser.parts).splitlines()
    rows = []
    y = 78
    for index, paragraph in enumerate(paragraphs):
        color = "#d7b46a" if index == 0 else "#ded3bf"
        for line in textwrap.wrap(paragraph, width=76, break_long_words=True):
            rows.append(f'<text x="28" y="{y}" fill="{color}">{html.escape(line)}</text>')
            y += 22
        y += 12
    height = y + 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}" role="img">
<title>Fortune</title>
<rect x="1" y="1" width="718" height="{height - 2}" rx="12" fill="#111018" stroke="#5a4437"/>
<text x="360" y="36" text-anchor="middle" fill="#d7b46a" font-family="Georgia, serif" font-size="22" font-weight="bold">Fortune</text>
<path d="M28 50 H692" stroke="#5a4437"/>
<g font-family="monospace" font-size="14">
{chr(10).join(rows)}
</g>
</svg>
'''


def generate_chess_asset(output_dir: Path) -> None:
    """Write the ASCII tracker independently of the rotating cards."""
    chart = generate_rating_chart()
    if chart is None:
        raise RuntimeError("No chess rating chart available")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "chess.svg").write_text(render_chess_svg(chart), encoding="utf-8")


def generate_spotlight_assets(output_dir: Path, *, seed: str) -> None:
    """Generate the cards and their matching fortune as one group."""
    catalog = load_projects(TEMPLATES / "projects.json")
    draws = draw_tarot_spread(pick_spotlight_projects(catalog, seed=seed), seed=seed)
    assets = {"fortune.svg": render_fortune_svg(render_fortune(draws))}
    for index, draw in enumerate(draws, start=1):
        assets[f"project-spotlight-{index}.svg"] = render_project_card_svg(draw)

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in assets.items():
        (output_dir / filename).write_text(content, encoding="utf-8")
