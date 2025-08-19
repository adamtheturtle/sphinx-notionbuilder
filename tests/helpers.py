"""
Test helper functions for Sphinx Notion Builder tests.
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph as UnoParagraph


def assert_rst_converts_to_paragraphs(
    rst_content: str,
    expected_paragraphs: list[UnoParagraph],
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Complete RST to Notion JSON conversion test.

    Takes RST content and expected paragraphs, builds the documentation
    using the Notion builder, and asserts the output matches the expected
    Ultimate Notion Paragraph objects.

    Args:
        rst_content: RST document content to build
        expected_paragraphs: List of Ultimate Notion Paragraph objects expected
        make_app: Sphinx test app factory function
        tmp_path: Temporary directory for test files
    """
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(data="")

    cleaned_content = textwrap.dedent(text=rst_content).strip()
    (srcdir / "index.rst").write_text(data=cleaned_content)

    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="notion",
        confoverrides={"extensions": ["sphinx_notionbuilder"]},
    )
    app.build()

    output_file = app.outdir / "index.json"
    with output_file.open() as f:
        generated_json: list[dict[str, Any]] = json.load(fp=f)

    expected_json = []
    for paragraph in expected_paragraphs:
        dumped_block = paragraph.obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        expected_json.append(dumped_block)

    assert generated_json == expected_json
