"""Workflow file helpers."""

from __future__ import annotations

import random
import re
from pathlib import Path

CRON_PATTERN = re.compile(r'(?P<prefix>cron:\s*["\'])(?P<schedule>[^"\']+)(?P<suffix>["\'])')


def randomize_rating_schedule(workflow_path: Path, *, seed: str | None = None) -> str:
    """Return workflow YAML with the rating-chart schedule minute randomized."""
    content = workflow_path.read_text(encoding="utf-8")
    rng = random.Random(seed)

    def replace_schedule(match: re.Match[str]) -> str:
        parts = match.group("schedule").split()
        if len(parts) != 5:
            raise ValueError(f"Could not parse cron schedule in {workflow_path}")

        parts[0] = str(rng.randrange(60))
        return f"{match.group('prefix')}{' '.join(parts)}{match.group('suffix')}"

    updated, count = CRON_PATTERN.subn(replace_schedule, content, count=1)

    if count != 1:
        raise ValueError(f"Could not find cron schedule in {workflow_path}")

    return updated
