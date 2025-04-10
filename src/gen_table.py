#!/usr/bin/env python3
"""Generate a markdown table from a JSON file containing project information."""

import json
import argparse
from pathlib import Path
from typing import TypedDict
from dataclasses import dataclass


class ProjectItem(TypedDict):
    """Type definition for a project item in the JSON data."""

    title: str
    link: str
    description: str


@dataclass
class TableConfig:
    """Configuration for the markdown table generation."""

    categories: dict[str, list[str]]
    layout: list[list[str]]
    centered_sections: list[str]


def load_project_data(file_path: Path) -> dict[str, list[ProjectItem]]:
    """
    Load and parse the project data from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the parsed project data

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos
        ) from e


def format_project_list(projects: list[ProjectItem]) -> str:
    """Format a list of projects as a bulleted markdown list."""
    return "<br>".join(
        f"• [{project['title']}]({project['link']}) - {project['description']}"
        for project in projects
    )


def generate_markdown_table(json_file: Path) -> str:
    """
    Generate a markdown table from the project data.

    Args:
        json_file: Path to the JSON file containing project data

    Returns:
        Formatted markdown table as a string
    """
    data = load_project_data(json_file)

    # Define the table structure
    project_categories: dict[str, list[str]] = {
        "Nix": [],
        "Go, Rust, Python, JavaScript, TypeScript": [],
        "Neovim Plugins": [],
    }

    # Populate the categories with formatted project entries
    for category, items in data.items():
        if category in project_categories:
            formatted_items = [
                f"• [{item['title']}]({item['link']}) - {item['description']}"
                for item in items
            ]
            project_categories[category].extend(formatted_items)

    # Generate the table content
    nix_content = "<br>".join(project_categories["Nix"])
    other_content = "<br>".join(
        project_categories["Go, Rust, Python, JavaScript, TypeScript"]
    )
    neovim_content = "<br>".join(project_categories["Neovim Plugins"])

    # Assemble the final markdown table
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


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a Markdown table from a JSON file containing project information."
    )
    parser.add_argument("file_path", type=Path, help="Path to the JSON file")
    args = parser.parse_args()

    try:
        markdown_table = generate_markdown_table(args.file_path)
        print(markdown_table)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
