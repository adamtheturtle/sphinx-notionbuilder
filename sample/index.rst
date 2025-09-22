Heading 1 with *bold*
=====================

.. contents::

.. toctree::

   other

.. This is a comment that demonstrates comment support.
   Comments should not appear in the final output.

Some text with a link to `Google <https://google.com>`_ and `<https://example.com>`_.

This is **bold** and *italic* and ``inline code``.

This text has :strike:`strike` formatting and :del:`deleted text` as well.

.. note::

   This is an important note that demonstrates the note admonition support.

   Some nested content:

   * First level item in note
   * Another first level item
   * Another first level item

     * Second level nested in note
     * Another second level item

       * Third level nested in note (deep!)
       * Another third level item

         * Fourth level nested in note (very deep!)
         * Another fourth level item
         * Another fourth level item

           * Fifth level nested in note (extremely deep!)
           * Another fifth level item

         * Back to fourth level in note

       * Back to third level in note

     * Back to second level in note

   * Back to first level in note

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

      .. warning::

         This is a warning that demonstrates the nested admonition support.

         .. warning::

            This is a warning that demonstrates the even deeper admonition support.

.. tip::

   This is a helpful tip that demonstrates the tip admonition support.

.. collapse:: Click to expand this section

   This content is hidden by default and can be expanded by clicking the toggle.

   It supports **all the same formatting** as regular content:

   * Bullet points
   * ``Code snippets``
   * *Emphasis* and **bold text**

   .. note::

      You can even nest admonitions inside collapsible sections!

   .. code-block:: python

      """Run code within a collapse."""


      def example_function() -> str:
          """Example code inside a collapsed section."""
          return "This is hidden by default"


      example_function()

.. collapse:: Another collapsible section

   You can have multiple collapsible sections in your document.

   Each one can contain different types of content.

.. code-block:: python

   """Python code."""


   def hello_world() -> int:
       """Return the answer."""
       return 42


   hello_world()

.. code-block:: console

   $ pip install sphinx-notionbuilder

Here's an example of including a file:

.. literalinclude:: conf.py
   :language: python

And with a caption:

.. literalinclude:: conf.py
   :language: python
   :caption: Example **Configuration** File

Some key features 👍:

* Easy integration with **Sphinx**
* Converts reStructuredText to Notion-compatible format

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
* Supports images with URLs
* Supports videos with URLs and local files

Numbered Lists
~~~~~~~~~~~~~~

The builder now supports numbered lists:

1. First numbered item
2. Second numbered item with **bold text**
3. Third numbered item with nested content

   1. First nested numbered item
   2. Second nested numbered item

      1. Deeply nested numbered item
      2. Another deeply nested item

   3. Back to second level

4. Fourth top-level item

Heading 2 with *italic*
-----------------------

Heading 3 with ``inline code``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Regular paragraph.

    This is a multi-line
    block quote with
    multiple lines.


Table Example
-------------

Here is a simple table:

+----------+----------+
| Header 1 | Header 2 |
+==========+==========+
| Cell 1   | Cell 2   |
+----------+----------+
| Cell 3   | Cell 4   |
+----------+----------+

Multi-Paragraph Rich Text Table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This table demonstrates the fix for issue #90 - tables with cells containing
multiple paragraphs where at least one paragraph includes rich text formatting:

+----------------------+-------------------------------+
| **Header Bold**      | *Header Italic*               |
+======================+===============================+
| **Bold text**        | *Italic text*                 |
| Normal text          | `Link <https://example.com>`_ |
+----------------------+-------------------------------+
| **First paragraph**  | *Italic paragraph*            |
|                      |                               |
| **Second paragraph** | Normal paragraph              |
|                      |                               |
| Normal text          | `link2 <https://google.com>`_ |
+----------------------+-------------------------------+

List Table with Stub Column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This table demonstrates a list table with a stub column (header column):

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * - Feature
     - Description
     - Status
   * - Bold text
     - Supports **bold** formatting
     - ✅ Working
   * - Italic text
     - Supports *italic* formatting
     - ✅ Working
   * - Code blocks
     - Supports ``inline code``
     - ✅ Working


Image Examples
--------------

Simple Image
~~~~~~~~~~~~

.. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop

Image with Alt Text
~~~~~~~~~~~~~~~~~~~

.. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop
   :alt: Mountain landscape with snow-capped peaks

Image with Alt Text
~~~~~~~~~~~~~~~~~~~

.. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop
   :alt: Beautiful mountain scenery

Local Image Example
~~~~~~~~~~~~~~~~~~~

.. image:: _static/test-image.png
   :alt: Local test image

Mixed Content with Images
~~~~~~~~~~~~~~~~~~~~~~~~~

Here's some text before the image.

.. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop

And here's some text after the image.

Video Examples
--------------

Simple Video
~~~~~~~~~~~~

.. video:: https://www.w3schools.com/html/mov_bbb.mp4

Video with Caption
~~~~~~~~~~~~~~~~~~

.. video:: https://www.w3schools.com/html/mov_bbb.mp4
   :caption: Sample video demonstrating video support

Local Video Example
~~~~~~~~~~~~~~~~~~~

.. video:: _static/test-video.mp4
   :caption: Local test video file

Mixed Content with Videos
~~~~~~~~~~~~~~~~~~~~~~~~~

Here's some text before the video.

.. video:: https://www.w3schools.com/html/mov_bbb.mp4
   :caption: Video embedded in content

And here's some text after the video.

.. collapse:: Long code block

   .. code-block:: python

      """Long code block to demonstrate working around Notion limits."""

      import sys

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")
      sys.stdout.write("Hello, world!")

.. collapse:: Over 100 blocks

   Test that we can upload > 100 blocks and child blocks.
   See https://developers.notion.com/reference/request-limits#limits-for-property-values.

   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
   * List item
