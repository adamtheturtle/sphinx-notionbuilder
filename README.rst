|Build Status| |PyPI|

Notion Builder for Sphinx
=========================

Builder for Sphinx which enables publishing documentation to Notion.

See a `sample document source`_ and the `published Notion page`_ for an example of what it can do.

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

* `sphinx-toolbox collapse`_
* `sphinx-toolbox rest_example`_
* `sphinxcontrib-video`_
* `sphinxnotes-strike`_
* `atsphinx-audioplayer`_
* `sphinx-immaterial task_lists`_
* `sphinx.ext.mathjax`_
* `sphinx-simplepdf`_
* `sphinx-iframes`_
* `sphinxcontrib-text-styles`_

See a `sample document source`_ and the `published Notion page`_ for an example of each of these.

To set these up, install the extensions you want to use and add them to your ``conf.py``, before ``sphinx_notion``:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "atsphinx.audioplayer",
       "sphinx.ext.mathjax",
       "sphinx_iframes",
       "sphinx_immaterial.task_lists",
       "sphinx_simplepdf",
       "sphinx_toolbox.collapse",
       "sphinx_toolbox.rest_example",
       "sphinxcontrib.video",
       "sphinxcontrib_text_styles",
       "sphinxnotes.strike",
       "sphinx_notion",
   ]

Supported Notion Block Types
----------------------------

The following syntax is supported:

- Headers
- Bulleted lists
- TODO lists (with checkboxes)
- Code blocks
- Table of contents
- Block quotes
- Callouts
- Collapsible sections (using the ``collapse`` directive from `sphinx-toolbox`_ )
- Rest-example blocks (using the ``rest-example`` directive from `sphinx-toolbox`_ )
- Images (with URLs or local paths)
- Videos (with URLs or local paths)
- Audio (with URLs or local paths)
- PDFs (with URLs or local paths)
- Embed blocks (using the ``iframe`` directive from `sphinx-iframes`_ )
- Tables
- Dividers (horizontal rules / transitions)
- Strikethrough text (using the ``strike`` role from `sphinxnotes-strike`_ )
- Colored text and text styles (bold, italic, monospace) (using various roles from `sphinxcontrib-text-styles`_ )
- Mathematical equations (inline and block-level, using the ``math`` role and directive from `sphinx.ext.mathjax`_ )
- Link to page blocks (using the ``notion-link-to-page`` directive)

See a `sample document source`_ and the `published Notion page`_.

All of these can be used in a way which means your documentation can still be rendered to HTML.

Directives
----------

``sphinx-notionbuilder`` provides custom directives for Notion-specific features:

``notion-link-to-page``
~~~~~~~~~~~~~~~~~~~~~~~

Creates a Notion "link to page" block that references another page in your Notion workspace.

**Usage:**

.. code-block:: rst

   .. notion-link-to-page:: PAGE_ID

**Parameters:**

- ``PAGE_ID``: The UUID of the Notion page you want to link to (without hyphens or with hyphens, both formats are accepted)

**Example:**

.. code-block:: rst

   .. notion-link-to-page:: 12345678-1234-1234-1234-123456789abc

This creates a clickable link block in Notion that navigates to the specified page when clicked.

Unsupported Notion Block Types
------------------------------

- Bookmark
- Breadcrumb
- Child database
- Child page
- Column and column list
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

#. Create a Notion integration at `notion-integrations`_

The integration token must have the following "Capabilities" set within the "Configuration" tab:

- **Content Capabilities**: Insert content, Update content, Read content
- **Comment Capabilities**: Read comments (required for checking if blocks have discussion threads for the ``--cancel-on-discussion`` option)
- **User Capabilities**: Read user information without email addresses (for bot identification)

In the "Access" tab, choose the pages and databases your integration can access.

#. Get your integration token and set it as an environment variable:

.. code-block:: console

   $ export NOTION_TOKEN="your_integration_token_here"

Usage
~~~~~


.. code-block:: console

   # The JSON file will be in the build directory, e.g. ./build/notion/index.json
   $ notion-upload --file path/to/output.json --parent-page-id parent_page_id --title "Page Title"

Or with a database parent:

.. code-block:: console

   $ notion-upload --file path/to/output.json --parent-database-id parent_database_id --title "Page Title"

Arguments:

- ``--file``: Path to the JSON file generated by the Notion builder
- ``--parent-page-id``: The ID of the parent page in Notion (must be shared with your integration) - mutually exclusive with ``--parent-database-id``
- ``--parent-database-id``: The ID of the parent database in Notion (must be shared with your integration) - mutually exclusive with ``--parent-page-id``
- ``--title``: Title for the new page in Notion
- ``--icon``: (Optional) Icon for the page (emoji)
- ``--cover-path``: (Optional) Path to a cover image file for the page

The command will create a new page if one with the given title doesn't exist, or update the existing page if one with the given title already exists.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-notionbuilder/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-notionbuilder/actions
.. |PyPI| image:: https://badge.fury.io/py/Sphinx-Notion-Builder.svg
   :target: https://badge.fury.io/py/Sphinx-Notion-Builder
.. |minimum-python-version| replace:: 3.11

.. _atsphinx-audioplayer: https://github.com/atsphinx/atsphinx-audioplayer
.. _notion-integrations: https://www.notion.so/my-integrations
.. _published Notion page: https://www.notion.so/Sphinx-Notionbuilder-Sample-2579ce7b60a48142a556d816c657eb55
.. _sample document source: https://raw.githubusercontent.com/adamtheturtle/sphinx-notionbuilder/refs/heads/main/sample/index.rst
.. _sphinx-iframes: https://pypi.org/project/sphinx-iframes/
.. _sphinx-immaterial task_lists: https://github.com/jbms/sphinx-immaterial
.. _sphinx-simplepdf: https://sphinx-simplepdf.readthedocs.io/
.. _sphinx-toolbox collapse: https://sphinx-toolbox.readthedocs.io/en/stable/extensions/collapse.html
.. _sphinx-toolbox rest_example: https://sphinx-toolbox.readthedocs.io/en/stable/extensions/rest_example.html
.. _sphinx-toolbox: https://sphinx-toolbox.readthedocs.io/en/stable/extensions/
.. _sphinx.ext.mathjax: https://www.sphinx-doc.org/en/master/usage/extensions/math.html#module-sphinx.ext.mathjax
.. _sphinxcontrib-text-styles: https://sphinxcontrib-text-styles.readthedocs.io/
.. _sphinxcontrib-video: https://sphinxcontrib-video.readthedocs.io
.. _sphinxnotes-strike: https://github.com/sphinx-toolbox/sphinxnotes-strike
