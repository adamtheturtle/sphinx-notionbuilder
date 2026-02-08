"""Configuration for Sphinx."""

import sys
from pathlib import Path

sys.path.insert(0, str(object=Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_toolbox.rest_example",
    "sphinx_notion",
]

autosummary_generate = True

suppress_warnings = ["ref.notion"]
