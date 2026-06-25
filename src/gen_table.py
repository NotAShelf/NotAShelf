#!/usr/bin/env python3
"""Generate the projects markdown table from the project catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.projects import load_projects, render_project_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the README projects table")
    parser.add_argument("file_path", type=Path, help="Path to the project JSON file")
    args = parser.parse_args()

    print(render_project_table(load_projects(args.file_path)))


if __name__ == "__main__":
    main()
