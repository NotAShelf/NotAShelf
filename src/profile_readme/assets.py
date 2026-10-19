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
<title>Lichess Rapid Rating Chart</title>
<style>
@media (prefers-color-scheme: light) {{
  svg {{
    --card-background: #ffffff;
    --card-border: #d1d9e0;
    --card-title: #1f2328;
    --card-text: #1f2328;
  }}
}}
.card {{ fill: var(--card-background, #0d1117); stroke: var(--card-border, #30363d); }}
.plot {{ fill: var(--card-text, #c9d1d9); }}
.title {{ fill: var(--card-title, #f0f6fc); }}
</style>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" class="card"/>
<g class="plot" font-family="DejaVu Sans Mono, monospace" font-size="14">
<text x="24" y="34" class="title" font-weight="bold">Lichess Rapid Rating Chart</text>
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
    """Render the reading as a wrapped SVG."""
    parser = _FortuneText()
    parser.feed(reading)
    paragraphs = "".join(parser.parts).splitlines()
    rows = []
    y = 82
    for paragraph in paragraphs:
        for line in textwrap.wrap(paragraph, width=76, break_long_words=True):
            rows.append(f'<text x="28" y="{y}">{html.escape(line)}</text>')
            y += 23
        y += 12
    height = y + 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}" role="img">
<title>Fortune</title>
<style>
:root {{ --paper: #141713; --ink: #ded6c3; --muted: #d0c9b8; --rule: #9f9987; --faint: #666a5b; }}
@media (prefers-color-scheme: light) {{
  :root {{ --paper: #f5eedf; --ink: #29271f; --muted: #645b4b; --rule: #8c7c60; --faint: #cbbd9f; }}
}}
</style>
<rect width="720" height="{height}" rx="9" fill="var(--paper)"/>
<rect x="7" y="7" width="706" height="{height - 14}" rx="5" fill="none" stroke="var(--rule)" stroke-width="0.7"/>
<rect x="11" y="11" width="698" height="{height - 22}" rx="3" fill="none" stroke="var(--faint)" stroke-width="0.5"/>
<text x="360" y="39" text-anchor="middle" fill="var(--ink)" font-family="Georgia, serif" font-size="24" font-variant="small-caps" letter-spacing="2">Fortune</text>
<path d="M28 55 H332 L360 48 L388 55 H692" fill="none" stroke="var(--rule)" stroke-width="0.6"/>
<g fill="var(--muted)" font-family="Georgia, 'Times New Roman', serif" font-size="16.5">
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
