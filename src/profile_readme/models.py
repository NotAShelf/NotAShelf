"""Shared project metadata models."""

from __future__ import annotations

from typing import NamedTuple, TypedDict


class ProjectItem(TypedDict):
    title: str
    link: str
    description: str


class ProjectCard(NamedTuple):
    category: str
    project: ProjectItem


ProjectCatalog = dict[str, list[ProjectItem]]
