#!/usr/bin/env python3
"""Build and publish the sample documentation to Notion.

Usage
-----
Set environment variables NOTION_TOKEN and NOTION_SAMPLE_PAGE_ID, then run::

    uv run python scripts/update_sample.py

Or pass them directly::

    NOTION_TOKEN=xxx NOTION_SAMPLE_PAGE_ID=yyy \
        uv run python scripts/update_sample.py

For a dry-run (shows commands without executing)::

    uv run python scripts/update_sample.py --dry-run
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Build and publish the sample documentation to Notion."""
    parser = argparse.ArgumentParser(
        description="Build and publish sample documentation to Notion.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the commands that would be run without executing them",
    )
    args = parser.parse_args()

    notion_token = os.environ.get("NOTION_TOKEN")
    notion_page_id = os.environ.get("NOTION_SAMPLE_PAGE_ID")

    if not notion_token:
        print(  # noqa: T201
            "Error: NOTION_TOKEN environment variable is required",
            file=sys.stderr,
        )
        return 1

    if not notion_page_id:
        print(  # noqa: T201
            "Error: NOTION_SAMPLE_PAGE_ID environment variable is required",
            file=sys.stderr,
        )
        return 1

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

    if args.dry_run:
        print("Would run:")  # noqa: T201
        print(f"  {' '.join(build_cmd)}")  # noqa: T201
        print()  # noqa: T201
        print("Then:")  # noqa: T201
        print(f"  {' '.join(upload_cmd)}")  # noqa: T201
        print()  # noqa: T201
        print("With environment:")  # noqa: T201
        print("  NOTION_TOKEN=***")  # noqa: T201
        print(f"  NOTION_SAMPLE_PAGE_ID={notion_page_id}")  # noqa: T201
        return 0

    # Clean build directory
    if build_dir.exists():
        shutil.rmtree(path=build_dir)

    print("Building sample documentation...")  # noqa: T201
    result = subprocess.run(args=build_cmd, check=False)
    if result.returncode != 0:
        print("Build failed!", file=sys.stderr)  # noqa: T201
        return int(result.returncode)

    print()  # noqa: T201
    print("Publishing to Notion...")  # noqa: T201
    result = subprocess.run(args=upload_cmd, check=False)
    if result.returncode != 0:
        print("Upload failed!", file=sys.stderr)  # noqa: T201
        return int(result.returncode)

    print()  # noqa: T201
    print("Done!")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
