"""Small template helper for repository-owned text templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping


PLACEHOLDER = re.compile(r"{{\s*([A-Z0-9_]+)\s*}}")


def render_template(path: Path, values: Mapping[str, object]) -> str:
    """Render a template with {{ PLACEHOLDER }} values."""
    template = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"Missing template value for {key} in {path}")

        return str(values[key])

    return PLACEHOLDER.sub(replace, template)
