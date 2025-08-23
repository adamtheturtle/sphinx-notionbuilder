Heading 1 with *bold*
=====================

.. contents::

Some text with a link to `Google <https://google.com>`_ and `<https://example.com>`_.

This is **bold** and *italic* and ``inline code``.

.. note::

   This is an important note that demonstrates the note admonition support.

.. warning::

   This is a warning that demonstrates the warning admonition support.

   .. code-block:: python

      """Python code nested in an admonition."""


      def hello_world() -> int:
          """Return the answer."""
          return 42


      hello_world()

   .. warning::

      This is a warning that demonstrates the warning admonition support.

.. tip::

   This is a helpful tip that demonstrates the tip admonition support.

.. code-block:: python

   """Python code."""


   def hello_world() -> int:
       """Return the answer."""
       return 42


   hello_world()

.. code-block:: console

   $ pip install sphinx-notionbuilder

Some key features:

* Easy integration with **Sphinx**
* Converts RST to Notion-compatible format

  * Supports nested bullet points (new!)
  * Deep nesting works too (limited to 2 levels)
  * This limit is described in https://developers.notion.com/reference/patch-block-children "For blocks that allow children, we allow up to two levels of nesting in a single request."
  * Note that the top level bullet-list is the "child" of the "body" so there is really only one level of nesting in the Notion API in one request.

* Supports code blocks with syntax highlighting
* Handles headings, links, and formatting
* Works with bullet points like this one
* Now supports note, warning, and tip admonitions!

Heading 2 with *italic*
-----------------------

Heading 3 with ``inline code``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Regular paragraph.

    This is a multi-line
    block quote with
    multiple lines.
