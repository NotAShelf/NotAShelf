set shell := ["bash", "-euo", "pipefail", "-c"]

python := ".venv/bin/python"

default: lint

setup:
    uv venv --python python3.11 .venv
    uv pip install --python {{python}} -r src/requirements.txt
    touch .venv/.requirements.stamp

format:
    ruff check --fix src
    ruff format src

lint:
    ruff format --check src
    ruff check src

compile:
    {{python}} -m compileall src

render-readme:
    {{python}} src/gen_readme.py

preview:
    magick generated/project-spotlight-1.svg generated/project-spotlight-2.svg generated/project-spotlight-3.svg +append /tmp/project-spotlight-preview.png

check: lint compile
