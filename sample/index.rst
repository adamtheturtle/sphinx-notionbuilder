Heading 1 with *bold*
=====================

.. contents::

Some text with a link to `Google <https://google.com>`_ and `<https://example.com>`_.

This is **bold** and *italic* and ``inline code``.

.. note::
   This is an important note that demonstrates the note admonition support.
   It will be converted to a Notion callout block with a note emoji.

.. warning::
   This is a warning that demonstrates the warning admonition support.
   It will be converted to a Notion callout block with a warning emoji and yellow background.

.. tip::
   This is a helpful tip that demonstrates the tip admonition support.
   It will be converted to a Notion callout block with a lightbulb emoji and green background.

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
  * Deep nesting works too

    * Level 3 nesting
    * Another level 3 item

      * Even level 4 nesting

* Supports code blocks with syntax highlighting
* Handles headings, links, and formatting
* Works with bullet points like this one
* Now supports note, warning, and tip admonitions!

Heading 2 with *italic*
-----------------------

Heading 3 with ``inline code``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Regular paragraph.

    This is a multiline
    block quote with
    multiple lines.
