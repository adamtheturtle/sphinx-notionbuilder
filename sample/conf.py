"""
Configuration for Sphinx.
"""

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
    "sphinx_notion",
]

# This is necessary because ``sphinx-iframes`` and ``sphinxcontrib.video``
# both implement a ``video`` directive.
# This is explained in the README.
suppress_warnings = ["app.add_directive"]
