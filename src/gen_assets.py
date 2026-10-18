#!/usr/bin/env python3
"""Stage complete, validated asset groups while isolating data-source failures."""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from profile_readme.assets import generate_chess_asset, generate_spotlight_assets

LOGGER = logging.getLogger(__name__)


def _generate_stats(output_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("gen_images.py")),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        timeout=600,
    )


def generate_assets(output_dir: Path, *, seed: str) -> bool:
    """Stage successful groups only, returning false if any group failed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(f"Staging directory must be empty: {output_dir}")

    groups = (
        ("statistics", ("overview.svg", "languages.svg"), _generate_stats),
        ("chess", ("chess.svg",), generate_chess_asset),
        (
            "spotlight",
            (
                "project-spotlight-1.svg",
                "project-spotlight-2.svg",
                "project-spotlight-3.svg",
                "fortune.svg",
            ),
            lambda directory: generate_spotlight_assets(directory, seed=seed),
        ),
    )
    succeeded = True
    with tempfile.TemporaryDirectory(prefix="profile-assets-") as temporary:
        for name, filenames, generate in groups:
            directory = Path(temporary) / name
            directory.mkdir()
            try:
                generate(directory)
                for filename in filenames:
                    root = ET.parse(directory / filename).getroot()
                    if root.tag != "{http://www.w3.org/2000/svg}svg":
                        raise ValueError(f"Not an SVG document: {filename}")
            except Exception:
                LOGGER.exception(
                    "Failed asset group: %s; existing published assets will be retained", name
                )
                succeeded = False
                continue
            for filename in filenames:
                shutil.copyfile(directory / filename, output_dir / filename)
            LOGGER.info("Generated and validated asset group: %s", name)
    return succeeded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Empty staging directory")
    parser.add_argument("--seed", default=dt.datetime.now(dt.timezone.utc).strftime("%G-W%V"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if not generate_assets(args.output_dir, seed=args.seed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
