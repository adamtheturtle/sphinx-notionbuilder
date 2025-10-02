|Build Status| |codecov| |PyPI|

Notion Builder for Sphinx
=========================

Extension for Sphinx which enables publishing documentation to Notion.

.. contents::

Installation
------------

``sphinx-notionbuilder`` is compatible with Python |minimum-python-version|\+.

.. code-block:: console

   $ pip install sphinx-notionbuilder

Add the following to ``conf.py`` to enable the extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = ["sphinx_notion"]

For collapsible sections (toggle blocks), also add the sphinx-toolbox collapse extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx_notion",
       "sphinx_toolbox.collapse",
   ]

For video support, also add the sphinxcontrib-video extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinxcontrib.video",  # Must be before sphinx_notion
       "sphinx_notion",
   ]

For strikethrough text support, also add the `sphinxnotes-strike <https://github.com/sphinx-toolbox/sphinxnotes-strike>`_ extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinxnotes.strike",  # Must be before sphinx_notion
       "sphinx_notion",
   ]

For audio support, also add the `atsphinx-audioplayer <https://github.com/atsphinx/atsphinx-audioplayer>`_ extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "atsphinx.audioplayer",
       "sphinx_notion",
   ]

For TODO list support, also add the `sphinx-immaterial <https://github.com/jbms/sphinx-immaterial>`_ task lists extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx_immaterial.task_lists",
       "sphinx_notion",
   ]

PDF support is included by default with the sphinx-notionbuilder extension.

Supported markup
----------------

The following syntax is supported:

- Headers
- Bulleted lists
- TODO lists (with checkboxes)
- Code blocks
- Table of contents
- Block quotes
- All standard admonitions (note, warning, tip, attention, caution, danger, error, hint, important)
- Collapsible sections (using sphinx-toolbox collapse directive)
- Images (with URLs or local paths)
- Videos (with URLs or local paths)
- Audio (with URLs or local paths)
- PDFs (with URLs or local paths)
- Tables
- Strikethrough text
- Colored text

See a `sample document source <https://raw.githubusercontent.com/adamtheturtle/sphinx-notionbuilder/refs/heads/main/sample/index.rst>`_ and the `published Notion page <https://www.notion.so/Sphinx-Notionbuilder-Sample-2579ce7b60a48142a556d816c657eb55>`_.

Using Audio
-----------

Audio files can be embedded using the ``audio`` directive. Both remote URLs and local file paths are supported:

.. code-block:: rst

   .. audio:: https://www.example.com/audio.mp3

   .. audio:: _static/local-audio.mp3

The audio will be rendered as an audio player in the generated Notion page.

Using PDFs
----------

PDF files can be embedded using the ``pdf-include`` directive. Both remote URLs and local file paths are supported.

.. code-block:: rst

   .. pdf-include:: https://www.example.com/document.pdf

   .. pdf-include:: _static/local-document.pdf

The PDF will be rendered as an embedded PDF viewer in the generated Notion page.

Using Colored Text
------------------

Colored text can be added using the `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_ extension. First, install the extension:

.. code-block:: console

   $ pip install sphinxcontrib-text-styles

Then add it to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinxcontrib_text_styles",
       "sphinx_notion",
   ]

You can then use colored text in your reStructuredText documents:

.. code-block:: rst

   This is :text-red:`red text`, :text-blue:`blue text`, and :text-green:`green text`.

The following colors are supported: red, blue, green, yellow, orange, purple, pink, brown, and gray.

Using TODO Lists
----------------

TODO lists with checkboxes can be created using the ``sphinx-immaterial.task_lists`` extension. Both bulleted and numbered lists support checkboxes:

.. code-block:: rst

   .. task-list::

       1. [x] Completed task
       2. [ ] Incomplete task
       3. [ ] Another task

   * [x] Bulleted completed task
   * [ ] Bulleted incomplete task

The checkboxes will be rendered as interactive TODO items in the generated Notion page, with completed tasks showing as checked and incomplete tasks as unchecked.

Unsupported Notion Block Types
------------------------------

- Bookmark
- Breadcrumb
- Child database
- Child page
- Column and column list
- Divider
- Embed
- Equation
- File
- Link preview
- Mention
- Synced block
- Template
- Heading with ``is_toggleable`` set to ``True``

Uploading Documentation to Notion
----------------------------------

After building your documentation with the Notion builder, you can upload it to Notion using the included command-line tool.

Prerequisites
~~~~~~~~~~~~~

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Get your integration token and set it as an environment variable:

.. code-block:: console

   $ export NOTION_TOKEN="your_integration_token_here"

Usage
~~~~~

.. code-block:: console

   $ notion-upload -f path/to/output.json -p parent_page_id -t "Page Title"

Arguments:

- ``--file``: Path to the JSON file generated by the Notion builder
- ``--parent-id``: The ID of the parent page or database in Notion (must be shared with your integration)
- ``--parent-type``: "page" or "database"
- ``--title``: Title for the new page in Notion

The command will create a new page if one with the given title doesn't exist, or update the existing page if one with the given title already exists.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-notionbuilder/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-notionbuilder/actions
.. |codecov| image:: https://codecov.io/gh/adamtheturtle/sphinx-notionbuilder/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/adamtheturtle/sphinx-notionbuilder
.. |PyPI| image:: https://badge.fury.io/py/Sphinx-Notion-Builder.svg
   :target: https://badge.fury.io/py/Sphinx-Notion-Builder
.. |minimum-python-version| replace:: 3.11
