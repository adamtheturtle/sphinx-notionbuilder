"""Configuration for Sphinx."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(object=Path(__file__).parent))

extensions = [
    "sphinxcontrib.video",
    "sphinx_iframes",
    "sphinxnotes.strike",
    "sphinxcontrib_text_styles",
    "sphinx_simplepdf",
    "sphinx_toolbox.collapse",
    "sphinx_toolbox.rest_example",
    "atsphinx.audioplayer",
    "sphinx_immaterial.task_lists",
    "sphinxcontrib.mermaid",
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx_jinja",
    "sphinx_notion",
]

# Workspace-specific Notion IDs used by the sample documentation.
#
# The sample references a Notion page, user and database that only exist in a
# particular workspace. To upload the sample to *any* workspace, these values
# are read from environment variables and rendered into ``.. jinja::`` blocks
# (provided by the ``sphinx_jinja`` extension) as ``{{ variable }}``
# placeholders. The values for the project's own demo workspace are committed
# in ``sample.env`` (sourced by CI and the publish scripts); regenerate that
# file for your own workspace with ``bootstrap-sample-env.py``.
jinja_contexts = {
    "notion": {
        "sample_page_id": os.environ["NOTION_SAMPLE_PAGE_ID"],
        "sample_user_id": os.environ["NOTION_SAMPLE_USER_ID"],
        "sample_database_id": os.environ["NOTION_SAMPLE_DATABASE_ID"],
    },
}

# `example.com` links are placeholder/demo links in docs and can intermittently
# fail certificate validation in CI environments.
linkcheck_ignore = [
    r"https://example\.com/?",
    r"https://www\.example\.com/.*",
]
