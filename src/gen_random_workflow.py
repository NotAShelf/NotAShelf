#!/usr/bin/env python3
"""Randomize a GitHub Actions workflow schedule."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_readme.workflows import randomize_workflow_schedule


def main() -> None:
    default_workflow = Path(".github/workflows/profile-readme.yml")
    parser = argparse.ArgumentParser(description="Randomize workflow cron schedule")
    parser.add_argument(
        "workflow_pos",
        nargs="?",
        type=Path,
        default=default_workflow,
        help="Workflow file path (positional form)",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=None,
        help="Workflow file path (keyword form)",
    )
    args = parser.parse_args()

    workflow = args.workflow or args.workflow_pos
    print(randomize_workflow_schedule(workflow), end="")


if __name__ == "__main__":
    main()
