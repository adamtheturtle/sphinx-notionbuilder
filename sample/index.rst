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
  * Deep nesting now works with multiple levels

    * Third level nesting is now supported
    * Fourth level also works

      * Fifth level nesting works too!
      * The upload script handles deep nesting automatically

    * Back to third level

  * Back to second level

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
