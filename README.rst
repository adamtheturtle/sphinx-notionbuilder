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

For collapsible sections (toggle blocks), also add the `sphinx-toolbox collapse <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/collapse.html>`_ extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx_notion",
       "sphinx_toolbox.collapse",
   ]

For video support, also add the `sphinxcontrib-video <https://sphinxcontrib-video.readthedocs.io>`_ extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       # sphinxcontrib.video must be before sphinx_notion
       "sphinxcontrib.video",
       "sphinx_notion",
   ]

If you are using ``sphinxcontrib.video`` with ``sphinx-iframes``, the warning ``app.add_directive`` will be raised.
This is because ``sphinxcontrib.video`` and ``sphinx-iframes`` both implement a ``video`` directive.
To suppress this warning, add the following to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   suppress_warnings = ["app.add_directive"]

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

For mathematical equation support, also add the `sphinx.ext.mathjax <https://www.sphinx-doc.org/en/master/usage/extensions/math.html#module-sphinx.ext.mathjax>`_ extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx.ext.mathjax",
       "sphinx_notion",
   ]

For rest-example blocks support, also add the `sphinx-toolbox <https://sphinx-toolbox.readthedocs.io/>`_ rest-example extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx_toolbox.rest_example",
       "sphinx_notion",
   ]

PDF support is included by default with the ``sphinx-notionbuilder`` extension and builds on the `sphinx-simplepdf <https://sphinx-simplepdf.readthedocs.io/>`_ extension.

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
- Collapsible sections (using the ``collapse`` directive from ``sphinx-toolbox``)
- Rest-example blocks (using the ``rest-example`` directive from ``sphinx-toolbox``)
- Images (with URLs or local paths)
- Videos (with URLs or local paths)
- Audio (with URLs or local paths)
- PDFs (with URLs or local paths)
- Embed blocks (using the ``iframe`` directive from ``sphinx-iframes``)
- Tables
- Strikethrough text
- Colored text and text styles (bold, italic, monospace)
- Mathematical equations (inline and block-level)

See a `sample document source <https://raw.githubusercontent.com/adamtheturtle/sphinx-notionbuilder/refs/heads/main/sample/index.rst>`_ and the `published Notion page <https://www.notion.so/Sphinx-Notionbuilder-Sample-2579ce7b60a48142a556d816c657eb55>`_.

Using Audio
-----------

Audio files can be embedded using the ``audio`` directive.
Both remote URLs and local file paths are supported:

.. code-block:: rst

   .. audio:: https://www.example.com/audio.mp3

   .. audio:: _static/local-audio.mp3

The audio will be rendered as an audio player in the generated Notion page.

Using PDFs
----------

PDF files can be embedded using the ``pdf-include`` directive.
Both remote URLs and local file paths are supported.

.. code-block:: rst

   .. pdf-include:: https://www.example.com/document.pdf

   .. pdf-include:: _static/local-document.pdf

The PDF will be rendered as an embedded PDF viewer in the generated Notion page.

Using Embed Blocks
------------------

Embed blocks can be created using the `sphinx-iframes <https://pypi.org/project/sphinx-iframes/>`_ extension. First, install the extension:

.. code-block:: console

   $ pip install sphinx-iframes

Then add it to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinx_iframes",  # Must be before sphinx_notion
       "sphinx_notion",
   ]

You can then use the ``iframe`` directive:

.. code-block:: rst

   .. iframe:: https://www.youtube.com/embed/dQw4w9WgXcQ

The iframes will be rendered as embed blocks in the generated Notion page, allowing you to embed external content like videos, interactive demos, or other web content.
However, if you are using ``sphinx-iframes`` with ``sphinxcontrib.video``, the warning ``app.add_directive`` will be raised.
This is because ``sphinx-iframes`` and ``sphinxcontrib.video`` both implement a ``video`` directive.
To suppress this warning, add the following to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   suppress_warnings = ["app.add_directive"]

Using Text Styles
-----------------

Text styles can be added using the `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_ extension. First, install the extension:

.. code-block:: console

   $ pip install sphinxcontrib-text-styles

Then add it to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinxcontrib_text_styles",
       "sphinx_notion",
   ]

You can then use various text styles in your reStructuredText documents:

Text Colors
~~~~~~~~~~~

.. code-block:: rst

   This is :text-red:`red text`, :text-blue:`blue text`, and :text-green:`green text`.

The following text colors are supported: red, blue, green, yellow, orange, purple, pink, brown, and gray.

Background Colors
~~~~~~~~~~~~~~~~~

.. code-block:: rst

   This is :bg-red:`red background text`, :bg-blue:`blue background text`, and :bg-green:`green background text`.

The following background colors are supported: red, blue, green, yellow, orange, purple, pink, brown, and gray.

Additional Text Styles
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: rst

   This is :text-bold:`bold text`, :text-italic:`italic text`, :text-mono:`monospace text`, :text-strike:`strikethrough text`, and :text-underline:`underlined text`.

The following additional text styles are supported:

- ``:text-bold:`text`` - Makes text bold
- ``:text-italic:`text`` - Makes text italic
- ``:text-mono:`text`` - Makes text monospace
- ``:text-strike:`text`` - Makes text strikethrough
- ``:text-underline:`text`` - Makes text underlined

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

Using Mathematical Equations
-----------------------------

Mathematical equations can be embedded using the ``sphinx.ext.mathjax`` extension.
Both inline and block-level equations are supported:

Inline Equations
~~~~~~~~~~~~~~~~

Inline equations can be written using the ``:math:`` role:

.. code-block:: rst

   This is an inline equation :math:`E = mc^2` in your text.

   Here are some more examples:

   - The quadratic formula: :math:`x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}`
   - Euler's identity: :math:`e^{i\pi} + 1 = 0`

Block Equations
~~~~~~~~~~~~~~~

Block-level equations can be written using the ``.. math::`` directive:

.. code-block:: rst

   .. math::

      E = mc^2

   The Schrödinger equation:

   .. math::

      i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)

The equations will be rendered as proper mathematical notation in the generated Notion page, with inline equations appearing within the text flow and block equations appearing as separate equation blocks.

Using Rest-Example Blocks
-------------------------

Rest-example blocks can be created using the `sphinx_toolbox.rest_example <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/rest_example.html>`_ extension to create example blocks that show both source code and expected output. These are rendered as callout blocks in Notion with nested code blocks:

Unsupported Notion Block Types
------------------------------

- Bookmark
- Breadcrumb
- Child database
- Child page
- Column and column list
- Divider
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

   $ notion-upload --file path/to/output.json --parent-id parent_page_id --parent-type page --title "Page Title" --sha-mapping notion-sha-mapping.json

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
