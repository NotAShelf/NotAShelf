"""Common filesystem paths used by profile generation scripts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
GENERATED = ROOT / "generated"
