Configuration
=============

``sphinx-notionbuilder`` provides configuration options in ``conf.py`` to enable automatic publishing to Notion after building your documentation.

Publishing Configuration
------------------------

To enable automatic publishing to Notion when building with the ``notion`` builder, add the following configuration options to your ``conf.py``:

.. skip doccmd[interrogate]: next

.. code-block:: python

   # Enable automatic publishing to Notion
   notion_publish = True

   # Required: Parent page or database ID
   notion_parent_page_id = "your-page-id-here"
   # OR
   notion_parent_database_id = "your-database-id-here"

   # Required: Title for the Notion page
   notion_page_title = "My Documentation"

   # Optional: Icon emoji for the page
   notion_page_icon = "📚"

   # Optional: Cover image URL
   notion_page_cover_url = "https://example.com/cover.jpg"

   # Optional: Cancel upload if blocks to be deleted have discussion threads
   notion_cancel_on_discussion = True

Configuration Options
---------------------

``notion_publish``
~~~~~~~~~~~~~~~~~~

:Type: ``bool``
:Default: ``False``

Enable automatic publishing to Notion after the build completes.
When set to ``True``, the documentation will be uploaded to Notion automatically after a successful build with the ``notion`` builder.

``notion_parent_page_id``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``None``

The ID of the parent Notion page under which the documentation will be published.
The page must be shared with your Notion integration.

This option is mutually exclusive with ``notion_parent_database_id``.

``notion_parent_database_id``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``None``

The ID of the parent Notion database under which the documentation will be published.
The database must be shared with your Notion integration.

This option is mutually exclusive with ``notion_parent_page_id``.

``notion_page_title``
~~~~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``None``

The title for the Notion page.
This is required when ``notion_publish`` is ``True``.

If a page with this title already exists under the parent, it will be updated.
Otherwise, a new page will be created.

``notion_page_icon``
~~~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``None``

An optional emoji icon for the Notion page (e.g., ``"📚"``).

``notion_page_cover_url``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``None``

An optional URL for a cover image for the Notion page.

``notion_cancel_on_discussion``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: ``bool``
:Default: ``False``

When set to ``True``, the upload will be cancelled with an error if any blocks that would be deleted have discussion threads attached to them.
This helps prevent accidentally losing discussion content.

Example Configuration
---------------------

Here is a complete example ``conf.py`` with publishing enabled:

.. skip doccmd[interrogate]: next

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = [
       "sphinxcontrib.video",
       "sphinx_notion",
   ]

   # Publishing configuration
   notion_publish = True
   notion_parent_page_id = "12345678-1234-1234-1234-123456789abc"
   notion_page_title = "My Project Documentation"
   notion_page_icon = "📖"
   notion_page_cover_url = "https://images.unsplash.com/photo-example"

Environment Setup
-----------------

Before publishing, ensure you have set up your Notion integration token as an environment variable:

.. code-block:: console

   $ export NOTION_TOKEN="your_integration_token_here"

See the main README for details on creating a Notion integration and setting up the required capabilities.
