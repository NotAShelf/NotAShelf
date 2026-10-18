"""SVG rendering for GitHub profile statistic cards."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Mapping

from profile_readme.paths import TEMPLATES
from profile_readme.templates import render_template


@dataclass(frozen=True)
class Theme:
    width: int = 360
    height: int = 320
    background: str = "#0d1117"
    border: str = "#30363d"
    title: str = "#f0f6fc"
    text: str = "#c9d1d9"
    muted: str = "#8b949e"
    accent: str = "#f78166"
    accent_alt: str = "#7ee787"
    track: str = "#21262d"
    radius: int = 8
    font: str = "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"


DEFAULT_THEME = Theme()


def render_overview(stats: Mapping[str, str], theme: Theme = DEFAULT_THEME) -> str:
    """Render the overview statistics card."""
    rows = [
        ("Stars", stats["stars"]),
        ("Forks", stats["forks"]),
        ("All-time contributions", stats["contributions"]),
        ("Authored commits, 90 days", stats["authored_commits"]),
        ("Lines changed, 90 days", stats["lines_changed"]),
        ("Views, past 14 days", stats["views"]),
        ("Repositories touched", stats["repos"]),
        ("Active repositories, 90 days", stats["authored_repos"]),
    ]

    row_markup = []
    for index, (label, value) in enumerate(rows):
        y = 84 + index * 24
        marker = (
            f"var(--card-accent, {theme.accent})"
            if index % 2 == 0
            else f"var(--card-accent-alt, {theme.accent_alt})"
        )
        row_markup.append(
            f'<circle cx="27" cy="{y - 4}" r="3" fill="{marker}" />'
            f'<text x="38" y="{y}" class="label">{escape(label)}</text>'
            f'<text x="330" y="{y}" text-anchor="end" class="value">{escape(value)}</text>'
        )

    return render_template(
        TEMPLATES / "overview.svg",
        {
            "WIDTH": theme.width,
            "HEIGHT": theme.height,
            "FONT": theme.font,
            "TITLE_COLOR": theme.title,
            "TEXT_COLOR": theme.text,
            "MUTED_COLOR": theme.muted,
            "BACKGROUND_COLOR": theme.background,
            "BORDER_COLOR": theme.border,
            "BORDER_RADIUS": theme.radius,
            "CARD_WIDTH": theme.width - 10,
            "CARD_HEIGHT": theme.height - 10,
            "CARD_TITLE": "GitHub Statistics",
            "DESCRIPTION": escape(f"GitHub statistics for {stats['name']}. {stats['scope']}"),
            "PERIOD": escape(stats["period"]),
            "ROWS": "\n".join(row_markup),
        },
    )


def render_languages(
    languages: Mapping[str, Mapping[str, object]],
    theme: Theme = DEFAULT_THEME,
    *,
    period: str = "Past 90 complete days",
    scope: str = "Search-indexed default branches accessible to the token; non-merge commits only.",
) -> str:
    """Render the language distribution card."""
    limit = 8
    sorted_languages = sorted(
        languages.items(),
        reverse=True,
        key=lambda item: float(item[1]["size"]),
    )
    if len(sorted_languages) > limit:
        remainder = sorted_languages[limit - 1 :]
        sorted_languages = sorted_languages[: limit - 1] + [
            (
                "Other languages",
                {
                    "size": sum(float(data["size"]) for _, data in remainder),
                    "prop": sum(float(data["prop"]) for _, data in remainder),
                    "color": f"var(--card-muted, {theme.muted})",
                },
            )
        ]

    x = 22.0
    bar_y = 275
    bar_width = 316.0
    progress_parts = [
        f'<rect x="22" y="{bar_y}" width="{bar_width:g}" height="10" rx="5" fill="var(--card-track, {theme.track})" />'
    ]
    list_parts = []
    for index, (name, data) in enumerate(sorted_languages):
        percent = float(data["prop"])
        width = max(0.0, bar_width * percent / 100)
        color = str(data.get("color") or f"var(--card-accent, {theme.accent})")
        progress_parts.append(
            f'<rect x="{x:g}" y="{bar_y}" width="{width:g}" height="10" fill="{escape(color)}" />'
        )
        x += width

        y = 84 + index * 24
        list_parts.append(
            f'<circle cx="27" cy="{y - 4}" r="3" fill="{escape(color)}" />'
            f'<text x="38" y="{y}" class="label">{escape(name)}</text>'
            f'<text x="330" y="{y}" text-anchor="end" class="value">{percent:0.2f}%</text>'
        )
    if not sorted_languages:
        list_parts.append(
            '<text x="22" y="100" class="label">No included authored changes.</text>'
            '<text x="22" y="124" class="label">Check the period and exclusion settings.</text>'
        )

    return render_template(
        TEMPLATES / "languages.svg",
        {
            "WIDTH": theme.width,
            "HEIGHT": theme.height,
            "FONT": theme.font,
            "TITLE_COLOR": theme.title,
            "TEXT_COLOR": theme.text,
            "MUTED_COLOR": theme.muted,
            "BACKGROUND_COLOR": theme.background,
            "BORDER_COLOR": theme.border,
            "BORDER_RADIUS": theme.radius,
            "CARD_WIDTH": theme.width - 10,
            "CARD_HEIGHT": theme.height - 10,
            "DESCRIPTION": escape(scope),
            "PERIOD": escape(period),
            "PROGRESS": "\n".join(progress_parts),
            "LANGUAGES": "\n".join(list_parts),
        },
    )
