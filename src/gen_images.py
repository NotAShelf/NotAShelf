#!/usr/bin/env python3
"""Generate SVG statistics cards for the profile README."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import aiohttp

from github_stats import Stats
from profile_readme.paths import GENERATED
from profile_readme.svg import render_languages, render_overview


def _split_env(name: str) -> set[str] | None:
    value = os.getenv(name)
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def _bool_env(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def generate_output_folder(output_dir: Path = GENERATED) -> None:
    """Create the generated asset directory."""
    output_dir.mkdir(parents=True, exist_ok=True)


async def generate_overview(stats: Stats, output_dir: Path = GENERATED) -> None:
    """Generate the profile overview SVG."""
    lines_added, lines_deleted = await stats.lines_changed
    payload = {
        "name": await stats.name,
        "stars": f"{await stats.stargazers:,}",
        "forks": f"{await stats.forks:,}",
        "contributions": f"{await stats.total_contributions:,}",
        "lines_changed": f"{lines_added + lines_deleted:,}",
        "views": f"{await stats.views:,}",
        "repos": f"{len(await stats.all_repos):,}",
    }
    (output_dir / "overview.svg").write_text(render_overview(payload), encoding="utf-8")


async def generate_languages(stats: Stats, output_dir: Path = GENERATED) -> None:
    """Generate the language distribution SVG."""
    (output_dir / "languages.svg").write_text(
        render_languages(await stats.languages),
        encoding="utf-8",
    )


async def main() -> None:
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("A personal access token is required to proceed")

    user = os.getenv("GITHUB_ACTOR")
    if not user:
        raise RuntimeError("GITHUB_ACTOR is required to proceed")

    generate_output_folder()
    async with aiohttp.ClientSession() as session:
        stats = Stats(
            user,
            access_token,
            session,
            exclude_repos=_split_env("EXCLUDED"),
            exclude_langs=_split_env("EXCLUDED_LANGS"),
            consider_forked_repos=_bool_env("COUNT_STATS_FROM_FORKS"),
        )
        await asyncio.gather(generate_languages(stats), generate_overview(stats))


if __name__ == "__main__":
    asyncio.run(main())
