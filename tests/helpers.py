"""
Test helper functions for Sphinx Notion Builder tests.
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pydantic
from sphinx.testing.util import SphinxTestApp
from ultimate_notion.blocks import Paragraph


def assert_rst_converts_to_notion_objects(
    rst_content: str,
    expected_objects: list[Paragraph],
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """
    The given rST content is converted to the given expected objects.
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

    expected_json: list[dict[str, Any]] = []
    for notion_object in expected_objects:
        obj_ref = notion_object.obj_ref
        assert isinstance(obj_ref, pydantic.BaseModel)
        dumped_block: dict[str, Any] = obj_ref.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        expected_json.append(dumped_block)

    assert generated_json == expected_json
