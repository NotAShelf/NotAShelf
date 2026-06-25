#!/usr/bin/env python3
"""Generate a demo project spotlight SVG card."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.paths import GENERATED, TEMPLATES
from profile_readme.projects import (
    load_projects,
    pick_spotlight_projects,
    render_spotlight,
)
from profile_readme.tarot import draw_tarot_spread, render_project_card_svg


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a project spotlight SVG card")
    parser.add_argument("--projects", type=Path, default=TEMPLATES / "projects.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED / "project-spotlight.svg",
    )
    parser.add_argument(
        "--spotlight-dir",
        type=Path,
        help="Write the three README spotlight cards to this directory",
    )
    parser.add_argument("--seed", default="demo")
    args = parser.parse_args()

    catalog = load_projects(args.projects)
    if args.spotlight_dir is not None:
        render_spotlight(catalog, seed=args.seed, output_dir=args.spotlight_dir)
        return

    card = draw_tarot_spread(
        pick_spotlight_projects(catalog, count=1, seed=args.seed),
        seed=args.seed,
    )[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_project_card_svg(card), encoding="utf-8")


if __name__ == "__main__":
    main()
