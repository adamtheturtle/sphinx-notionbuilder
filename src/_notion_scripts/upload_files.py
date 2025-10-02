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
from ultimate_notion import Session
from ultimate_notion.blocks import PDF as UnoPDF  # noqa: N811
from ultimate_notion.blocks import Audio as UnoAudio
from ultimate_notion.blocks import Block
from ultimate_notion.blocks import Image as UnoImage
from ultimate_notion.blocks import Video as UnoVideo
from ultimate_notion.obj_api.blocks import Block as UnoObjAPIBlock


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
def _extract_file_urls_from_blocks(*, blocks: list[Block]) -> set[str]:
    """
    Extract file URLs from blocks that contain files.
    """
    file_urls: set[str] = set()

    for block in blocks:
        if isinstance(
            block, (UnoImage, UnoVideo, UnoAudio, UnoPDF)
        ) and block.url.startswith("file://"):
            file_urls.add(block.url)

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

    file_sha = _calculate_file_sha(file_path=file_path)
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
    block_details = json.loads(s=build_content)
    blocks = [
        Block.wrap_obj_ref(UnoObjAPIBlock.model_validate(obj=details))
        for details in block_details
    ]

    file_urls = _extract_file_urls_from_blocks(blocks=blocks)

    referenced_shas: set[str] = set()
    session: Session | None = None

    for file_url in file_urls:
        file_sha, notion_url = _process_file_url(
            url=file_url, sha_mapping=sha_mapping
        )

        if file_sha:
            referenced_shas.add(file_sha)

            if notion_url is None:
                if session is None:
                    session = Session()

                parsed = urlparse(url=file_url)
                file_path = Path(url2pathname(parsed.path))  # type: ignore[misc]

                with file_path.open(mode="rb") as file_stream:
                    uploaded_file = session.upload(
                        file=file_stream,
                        file_name=file_path.name,
                    )

                uploaded_file.wait_until_uploaded()

                uploaded_url = getattr(uploaded_file, "url", None)
                if uploaded_url is None and hasattr(uploaded_file, "get_url"):
                    uploaded_url = uploaded_file.get_url()  # type: ignore[assignment]
                if uploaded_url is None and hasattr(
                    uploaded_file, "get_file_url"
                ):
                    uploaded_url = uploaded_file.get_file_url()  # type: ignore[assignment]
                if uploaded_url is None:
                    raise RuntimeError(
                        f"Unable to determine Notion URL for uploaded file: {file_path}"
                    )

                notion_url = str(uploaded_url)
                sha_mapping[file_sha] = notion_url
                click.echo(
                    message=f"Uploaded file: {file_path.name} ({file_sha[:16]}...)"
                )
            else:
                click.echo(message=f"File already mapped: {file_sha[:16]}...")

    for sha in list(sha_mapping.keys()):
        if sha not in referenced_shas:
            notion_url = sha_mapping.pop(sha)
            click.echo(
                message=f"Removed unused mapping: {sha[:16]}... -> {notion_url}"
            )

    # Save updated mapping
    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    mapping_file.write_text(
        data=json.dumps(obj=sha_mapping, indent=2, sort_keys=True),
        encoding="utf-8",
    )
