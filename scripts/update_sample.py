#!/usr/bin/env python3
"""Build and publish the sample documentation to Notion.

Usage
-----
Set environment variables NOTION_TOKEN and NOTION_SAMPLE_PAGE_ID, then run::

    uv run python scripts/update_sample.py

Or pass them directly::

    NOTION_TOKEN=xxx NOTION_SAMPLE_PAGE_ID=yyy \
        uv run python scripts/update_sample.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

import click


@click.command()
@click.option(
    "--notion-token",
    envvar="NOTION_TOKEN",
    required=True,
    help="Notion API token",
)
@click.option(
    "--notion-page-id",
    envvar="NOTION_SAMPLE_PAGE_ID",
    required=True,
    help="ID of the parent Notion page",
)
def main(
    notion_token: str,
    notion_page_id: str,
) -> None:
    """Build and publish the sample documentation to Notion."""
    del notion_token  # Used by environment, not directly
    repo_root = Path(__file__).resolve().parent.parent
    sample_dir = repo_root / "sample"
    build_dir = repo_root / "build-sample"

    sample_dir_str = str(object=sample_dir)
    build_dir_str = str(object=build_dir)
    index_json_str = str(object=build_dir / "index.json")

    build_cmd = [
        "uv",
        "run",
        "--extra=sample",
        "sphinx-build",
        "-W",
        "-b",
        "notion",
        sample_dir_str,
        build_dir_str,
    ]

    upload_cmd = [
        "uv",
        "run",
        "--all-extras",
        "notion-upload",
        "--parent-page-id",
        notion_page_id,
        "--file",
        index_json_str,
        "--title",
        "Sphinx-Notionbuilder Sample",
        "--icon",
        "🐍",
    ]

    # Clean build directory
    if build_dir.exists():
        shutil.rmtree(path=build_dir)

    click.echo(message="Building sample documentation...")
    result = subprocess.run(args=build_cmd, check=False)
    if result.returncode != 0:
        click.echo(message="Build failed!", err=True)
        sys.exit(result.returncode)

    click.echo()
    click.echo(message="Publishing to Notion...")
    result = subprocess.run(args=upload_cmd, check=False)
    if result.returncode != 0:
        click.echo(message="Upload failed!", err=True)
        sys.exit(result.returncode)

    click.echo()
    click.echo(message="Done!")


if __name__ == "__main__":
    main()
