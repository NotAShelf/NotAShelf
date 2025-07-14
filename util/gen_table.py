#!/usr/bin/env python3
"""Generate a markdown table from a JSON file containing project information."""

import json
from pathlib import Path
from typing import TypedDict


class ProjectItem(TypedDict):
    title: str
    link: str
    description: str


def load_project_data(file_path: Path) -> dict[str, list[ProjectItem]]:
    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos
        ) from e


def generate_markdown_table(json_file: Path) -> str:
    data = load_project_data(json_file)
    project_categories: dict[str, list[str]] = {
        "Nix": [],
        "Go, Rust, Python, JavaScript, TypeScript": [],
        "Neovim Plugins": [],
    }
    for category, items in data.items():
        if category in project_categories:
            formatted_items = [
                f"• [{item['title']}]({item['link']}) - {item['description']}"
                for item in items
            ]
            project_categories[category].extend(formatted_items)
    nix_content = "<br>".join(project_categories["Nix"])
    other_content = "<br>".join(
        project_categories["Go, Rust, Python, JavaScript, TypeScript"]
    )
    neovim_content = "<br>".join(project_categories["Neovim Plugins"])
    table = (
        "| **Nix** | **Go, Rust, Python, JavaScript, TypeScript** |\n"
        "| --- | --- |\n"
        f"| {nix_content} | {other_content} |\n\n"
        "<div align='center'>\n\n"
        "| **Neovim Plugins** |\n"
        "| --- |\n"
        f"| {neovim_content} |\n"
        "</div>\n"
    )
    return table
