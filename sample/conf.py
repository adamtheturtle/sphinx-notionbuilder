"""
Configuration for Sphinx.
"""

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
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_notion",
]

autosummary_generate = True
