"""Upload files and manage SHA mapping for Notion file uploads.

This CLI tool processes a JSON build file and updates the SHA mapping
based on what files are actually used in the build.
"""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import click
from beartype import beartype


@beartype
def _calculate_file_sha(*, file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """
    sha256_hash = hashlib.sha256()
    with file_path.open(mode="rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@beartype
def _extract_file_urls_from_blocks(*, blocks: list[dict]) -> set[str]:
    """
    Extract file URLs from blocks that contain files.
    """
    file_urls = set()

    for block in blocks:
        # Check for image blocks with file URLs
        if block.get("type") == "image" and "image" in block:
            image_data = block["image"]
            if "file" in image_data and "url" in image_data["file"]:
                url = image_data["file"]["url"]
                if url and url.startswith("file://"):
                    file_urls.add(url)

        # Check for video blocks with file URLs
        elif block.get("type") == "video" and "video" in block:
            video_data = block["video"]
            if "file" in video_data and "url" in video_data["file"]:
                url = video_data["file"]["url"]
                if url and url.startswith("file://"):
                    file_urls.add(url)

        # Check for audio blocks with file URLs
        elif block.get("type") == "audio" and "audio" in block:
            audio_data = block["audio"]
            if "file" in audio_data and "url" in audio_data["file"]:
                url = audio_data["file"]["url"]
                if url and url.startswith("file://"):
                    file_urls.add(url)

        # Check for PDF blocks with file URLs
        elif block.get("type") == "pdf" and "pdf" in block:
            pdf_data = block["pdf"]
            if "file" in pdf_data and "url" in pdf_data["file"]:
                url = pdf_data["file"]["url"]
                if url and url.startswith("file://"):
                    file_urls.add(url)

    return file_urls


@beartype
def _process_file_url(
    *,
    url: str,
    sha_mapping: dict[str, str],
) -> tuple[str, str | None]:
    """Process a file URL and return (sha, notion_url).

    Returns (sha, None) if the file is not mapped.
    """
    parsed = urlparse(url=url)
    if parsed.scheme != "file":
        return "", None

    # Ignore ``mypy`` error as the keyword arguments are different across
    # Python versions and platforms.
    file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]

    if not file_path.exists():
        return "", None

    # Calculate SHA
    file_sha = _calculate_file_sha(file_path=file_path)

    # Check if mapped
    notion_url = sha_mapping.get(file_sha)

    return file_sha, notion_url


@click.command()
@click.option(
    "--mapping-file",
    help="Path to the SHA mapping JSON file",
    required=True,
    type=click.Path(
        dir_okay=False,
        exists=True,
        file_okay=True,
        path_type=Path,
    ),
)
@click.option(
    "--build-file",
    help="Path to the JSON build file to process",
    required=True,
    type=click.Path(
        dir_okay=False,
        exists=True,
        file_okay=True,
        path_type=Path,
    ),
)
@beartype
def main(
    *,
    mapping_file: Path,
    build_file: Path,
) -> None:
    """
    Upload files to Notion and update the SHA mapping.
    """
    mapping_file_content = mapping_file.read_text(encoding="utf-8")
    sha_mapping = dict(json.loads(s=mapping_file_content))

    build_content = build_file.read_text(encoding="utf-8")
    blocks = json.loads(s=build_content)

    file_urls = _extract_file_urls_from_blocks(blocks=blocks)

    referenced_shas: set[str] = set()

    for file_url in file_urls:
        file_sha, notion_url = _process_file_url(
            url=file_url, sha_mapping=sha_mapping
        )

        if file_sha:
            referenced_shas.add(file_sha)

            if notion_url is None:
                # File is referenced but not mapped - we need to upload it
                # For now, we'll just note this
                click.echo(message=f"File needs upload: {file_sha[:16]}...")
                # TODO: Actually upload the file and get the Notion URL
                # For now, we'll skip this case
            else:
                click.echo(message=f"File already mapped: {file_sha[:16]}...")

    for sha in list(sha_mapping.keys()):
        if sha not in referenced_shas:
            notion_url = sha_mapping.pop(sha)

    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    mapping_file.write_text(
        data=json.dumps(obj=sha_mapping, indent=2, sort_keys=True),
        encoding="utf-8",
    )
