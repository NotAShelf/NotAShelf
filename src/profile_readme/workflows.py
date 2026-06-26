"""Workflow file helpers."""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

CRON_PATTERN = re.compile(
    r"""(?P<prefix>^\s*-?\s*cron:\s*)(?P<schedule>"[^"]*"|'[^']*'|[^#\n\r]+)""",
    re.MULTILINE,
)


def randomize_workflow_schedule(
    workflow_path: Path, *, seed: str | None = None
) -> str:
    """Return workflow YAML with the first cron schedule randomized."""
    content = workflow_path.read_text(encoding="utf-8")
    rng = random.Random(seed)

    def replace_schedule(match: re.Match[str]) -> str:
        schedule_field = match.group("schedule")
        suffix = ""
        if "#" in schedule_field:
            schedule_field, suffix = schedule_field.split("#", 1)
            suffix = f" #{suffix}".rstrip()

        raw_schedule = schedule_field.strip()
        if not raw_schedule:
            raise ValueError(f"Could not parse cron schedule in {workflow_path}")

        quote = ""
        if raw_schedule[0] == raw_schedule[-1] and raw_schedule[0] in ('"', "'"):
            quote = raw_schedule[0]
            raw_schedule = raw_schedule[1:-1]

        parts = raw_schedule.split()
        if len(parts) != 5:
            raise ValueError(f"Could not parse cron schedule in {workflow_path}")

        parts[0] = str(rng.randrange(60))
        return f"{match.group('prefix')}{quote}{' '.join(parts)}{quote}{suffix}"

    updated, count = CRON_PATTERN.subn(replace_schedule, content, count=1)

    if count != 1:
        print(
            f"Warning: no cron schedule found in {workflow_path}, leaving file unchanged.",
            file=sys.stderr,
        )
        return content

    return updated
