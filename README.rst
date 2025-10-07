|Build Status| |PyPI|

Notion Builder for Sphinx
=========================

Builder for Sphinx which enables publishing documentation to Notion.

See a `sample document source <https://raw.githubusercontent.com/adamtheturtle/sphinx-notionbuilder/refs/heads/main/sample/index.rst>`_ and the `published Notion page <https://www.notion.so/Sphinx-Notionbuilder-Sample-2579ce7b60a48142a556d816c657eb55>`_ for an example of what it can do.

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

``sphinx-notionbuilder`` also works with a variety of Sphinx extensions:

* `sphinx-toolbox collapse <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/collapse.html>`_
* `sphinx-toolbox rest_example <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/rest_example.html>`_
* `sphinxcontrib-video <https://sphinxcontrib-video.readthedocs.io>`_
* `sphinxnotes-strike <https://github.com/sphinx-toolbox/sphinxnotes-strike>`_
* `atsphinx-audioplayer <https://github.com/atsphinx/atsphinx-audioplayer>`_
* `sphinx-immaterial task_lists <https://github.com/jbms/sphinx-immaterial>`_
* `sphinx.ext.mathjax <https://www.sphinx-doc.org/en/master/usage/extensions/math.html#module-sphinx.ext.mathjax>`_
* `sphinx-simplepdf <https://sphinx-simplepdf.readthedocs.io/>`_
* `sphinx-iframes <https://pypi.org/project/sphinx-iframes/>`_

See a `sample document source <https://raw.githubusercontent.com/adamtheturtle/sphinx-notionbuilder/refs/heads/main/sample/index.rst>`_ and the `published Notion page <https://www.notion.so/Sphinx-Notionbuilder-Sample-2579ce7b60a48142a556d816c657eb55>`_ for an example of each of these.

To set these up, install the extensions you want to use and add them to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "atsphinx.audioplayer",
       "sphinx_toolbox.collapse",
       "sphinxcontrib.video",
       "sphinxnotes.strike",
       "sphinx_immaterial.task_lists",
       "sphinx_toolbox.rest_example",
       "sphinx.ext.mathjax",
       "sphinx_notion",  # Put ``sphinx_notion`` after the other extensions.
   ]

If you are using ``sphinxcontrib.video`` with ``sphinx-iframes``, the warning ``app.add_directive`` will be raised.
This is because ``sphinxcontrib.video`` and ``sphinx-iframes`` both implement a ``video`` directive.
To suppress this warning, add the following to your ``conf.py``:

.. code-block:: python

   """Configuration for Sphinx."""

   suppress_warnings = ["app.add_directive"]

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

.. code-block:: python

   """Configuration for Sphinx."""

   suppress_warnings = ["app.add_directive"]

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

Build documentation with the ``notion`` builder.
For eaxmple:

.. code-block:: console

   $ sphinx-build -W -b notion source build/notion

After building your documentation with the Notion builder, you can upload it to Notion using the included command-line tool.

Prerequisites
~~~~~~~~~~~~~

#. Create a Notion integration at https://www.notion.so/my-integrations
#. Get your integration token and set it as an environment variable:

.. code-block:: console

   $ export NOTION_TOKEN="your_integration_token_here"

Usage
~~~~~

.. code-block:: console

   # The JSON file will be in the build directory, e.g. ./build/notion/index.json
   $ notion-upload --file path/to/output.json --parent-id parent_page_id --parent-type page --title "Page Title" --sha-mapping notion-sha-mapping.json

Arguments:

- ``--file``: Path to the JSON file generated by the Notion builder
- ``--parent-id``: The ID of the parent page or database in Notion (must be shared with your integration)
- ``--parent-type``: "page" or "database"
- ``--title``: Title for the new page in Notion

The command will create a new page if one with the given title doesn't exist, or update the existing page if one with the given title already exists.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-notionbuilder/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-notionbuilder/actions
.. |PyPI| image:: https://badge.fury.io/py/Sphinx-Notion-Builder.svg
   :target: https://badge.fury.io/py/Sphinx-Notion-Builder
.. |minimum-python-version| replace:: 3.11
