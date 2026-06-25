"""Workflow file helpers."""

from __future__ import annotations

import random
import re
from pathlib import Path

CRON_PATTERN = re.compile(r'cron:\s+"0 \*/([1-9]|1[0-9]|2[0-4]) \* \* \*"')


def randomize_rating_schedule(workflow_path: Path, *, seed: str | None = None) -> str:
    """Return workflow YAML with the rating-chart schedule randomized."""
    content = workflow_path.read_text(encoding="utf-8")
    rng = random.Random(seed)
    replacement = f'cron: "0 */{rng.randint(1, 8)} * * *"'
    updated, count = CRON_PATTERN.subn(replacement, content, count=1)

    if count != 1:
        raise ValueError(f"Could not find hourly cron schedule in {workflow_path}")

    return updated
