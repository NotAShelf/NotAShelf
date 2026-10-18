#!/usr/bin/env python3
"""Generate SVG statistics cards for the profile README."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import aiohttp

from github_stats import Stats
from profile_readme.paths import GENERATED
from profile_readme.svg import render_languages, render_overview

AUTHORSHIP_SCOPE = (
    "Added and deleted lines in non-merge commits authored by the configured GitHub user, "
    "committed during the stated 90 complete UTC days. Includes upstream repositories "
    "and owned or known contributed forks irrespective of COUNT_STATS_FROM_FORKS. "
    "Discovery covers GitHub search-indexed default branches plus default branches of "
    "forks found through owned/contributed repository listings accessible to the token; "
    "undiscoverable repositories and non-default branches may be absent. GitHub search "
    "considers at most 4,000 repositories per query. Identical commit SHAs count once. "
    "Language detection uses pinned GitHub Linguist filenames and content rules. "
    "If the diff is inconclusive, the repository's language list can resolve a filename "
    "only when one candidate matches. Percentages count changed lines, not repository sizes. "
    "Unresolved filenames appear as Ambiguous or Unclassified."
)


def _period(stats: Stats) -> str:
    return f"{stats.authored_start} – {stats.authored_end} · UTC"


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
        "authored_commits": f"{stats.authored_commits:,}",
        "authored_repos": f"{stats.authored_repo_count:,}",
        "scope": AUTHORSHIP_SCOPE,
        "period": _period(stats),
    }
    (output_dir / "overview.svg").write_text(render_overview(payload), encoding="utf-8")


async def generate_languages(stats: Stats, output_dir: Path = GENERATED) -> None:
    """Generate the language distribution SVG."""
    (output_dir / "languages.svg").write_text(
        render_languages(await stats.languages, period=_period(stats), scope=AUTHORSHIP_SCOPE),
        encoding="utf-8",
    )


async def main(output_dir: Path = GENERATED) -> None:
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("A personal access token is required to proceed")

    user = os.getenv("PROFILE_USERNAME")
    if not user:
        raise RuntimeError("PROFILE_USERNAME is required to proceed")

    generate_output_folder(output_dir)
    async with (
        asyncio.timeout(540),
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session,
    ):
        stats = Stats(
            user,
            access_token,
            session,
            exclude_repos=_split_env("EXCLUDED"),
            exclude_langs=_split_env("EXCLUDED_LANGS"),
            consider_forked_repos=_bool_env("COUNT_STATS_FROM_FORKS"),
        )
        await stats.get_stats()
        await generate_languages(stats, output_dir)
        await generate_overview(stats, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=GENERATED)
    asyncio.run(main(parser.parse_args().output_dir))
