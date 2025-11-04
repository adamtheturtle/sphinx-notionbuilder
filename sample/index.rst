Heading 1 with *bold*
=====================

.. contents::


Comments
~~~~~~~~

.. rest-example::

   .. This is a comment that demonstrates comment support.
      Comments should not appear in the final output.

Text Formatting
~~~~~~~~~~~~~~~

.. rest-example::

   This is **bold** and *italic* and ``inline code``.

   This text has :strike:`strike` formatting and :del:`deleted text` as well.

   The builder supports colored text using `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_:

   This is :text-red:`red text`, :text-blue:`blue text`, :text-green:`green text`, :text-yellow:`yellow text`, :text-orange:`orange text`, :text-purple:`purple text`, :text-pink:`pink text`, :text-brown:`brown text`, and :text-gray:`gray text`.

   The builder also supports background colors using `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_:

   This is :bg-red:`red background text`, :bg-blue:`blue background text`, :bg-green:`green background text`, :bg-yellow:`yellow background text`, :bg-orange:`orange background text`, :bg-purple:`purple background text`, :bg-pink:`pink background text`, :bg-brown:`brown background text`, and :bg-gray:`gray background text`.

   The builder supports additional text styles: :text-bold:`bold text`, :text-italic:`italic text`, :text-mono:`monospace text`, :text-strike:`strikethrough text`, and :text-underline:`underlined text`.

   The builder supports keyboard shortcuts using the standard ``:kbd:`` role: Press :kbd:`Ctrl+C` to copy, :kbd:`Ctrl+V` to paste.

   The builder supports file paths using the standard ``:file:`` role: Edit the :file:`config.py` file or check :file:`/etc/hosts`.

Links
~~~~~

Link with a title
^^^^^^^^^^^^^^^^^

.. rest-example::

   Link to `Google <https://google.com>`_

Link with no title
^^^^^^^^^^^^^^^^^^

.. rest-example::

   Link to `<https://google.com>`_

Link to Notion
^^^^^^^^^^^^^^

.. rest-example::

   Link to `Notion page with title <https://www.notion.so/Other-page-2a19ce7b60a4807dbae7c12161f12056>`_

   Link to Notion page without title `<https://www.notion.so/Other-page-2a19ce7b60a4807dbae7c12161f12056>`_

Link to Notion Page Block
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rest-example::

   .. notion-link-to-page:: 2a19ce7b60a4807dbae7c12161f12056

Admonitions
~~~~~~~~~~~

.. rest-example::

   .. note::

      This is a note that demonstrates the note admonition support.

   .. warning::

      This is a warning that demonstrates the warning admonition support.

   .. tip::

      This is a helpful tip that demonstrates the tip admonition support.

   .. attention::

      This is an attention admonition that requires your attention.

   .. caution::

      This is a caution admonition that warns about potential issues.

   .. danger::

      This is a danger admonition that indicates a dangerous situation.

   .. error::

      This is an error admonition that shows error information.

   .. hint::

      This is a hint admonition that provides helpful hints.

   .. important::

      This is an important admonition that highlights important information.

   .. admonition:: Custom Admonition Title

      This is a generic admonition with a custom title.
      You can use this for any type of callout that doesn't fit the standard admonition types.

Collapsible Content
~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. collapse:: Click to expand this section

      This content is hidden by default and can be expanded by clicking the toggle.

      It supports **all the same formatting** as regular content.

Dividers
~~~~~~~~

There will be a divider here (this does not work within collapse blocks).

--------

Including Files
~~~~~~~~~~~~~~~

.. rest-example::

   Here's an example of including a file:

   .. literalinclude:: conf.py
      :language: python

   And with a caption:

   .. literalinclude:: conf.py
      :language: python
      :caption: Example **Configuration** File

Bullet Lists
~~~~~~~~~~~~

.. rest-example::

   This demonstrates the new support for nesting various content types within bullet lists:

   * First bullet point with **bold text**

     This is a paragraph nested within a bullet list item. It should work now!

     .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop
        :alt: Nested image in bullet list

     * Nested bullet point
     * Another nested bullet

       * Deeply nested bullet

   * Second bullet point with *italic text*

     Here's some code nested within a bullet list:

     .. code-block:: python

         """Python code."""

         import sys

         sys.stdout.write("Hello, world!")

     And here's a note admonition nested within the bullet list:

     .. note::

        This is a note that's nested within a bullet list item. This should work now!

   * Third bullet point

     This bullet point contains a table:

     +----------+----------+
     | Header 1 | Header 2 |
     +==========+==========+
     | Cell 1   | Cell 2   |
     +----------+----------+
     | Cell 3   | Cell 4   |
     +----------+----------+

Numbered Lists
~~~~~~~~~~~~~~

.. rest-example::

   The builder now supports numbered lists:

   #. First numbered item
   #. Second numbered item with **bold text**
   #. Third numbered item with nested content

      #. First nested numbered item
      #. Second nested numbered item

         #. Deeply nested numbered item
         #. Another deeply nested item

      #. Back to second level

   #. Fourth top-level item

Task Lists
~~~~~~~~~~

.. rest-example::

   The builder supports task lists with checkboxes:

   .. task-list::

      1. [x] Task A
      2. [ ] Task B

         .. task-list::
            :clickable:

            * [x] Task B1
            * [x] Task B2
            * [] Task B3

            A rogue paragraph.

            - A list item without a checkbox.
            - [ ] Another bullet point.

      3. [ ] Task C

Block Quotes
~~~~~~~~~~~~

.. rest-example::

   Regular paragraph.

         This is a multi-line
         block quote with
         multiple lines.

         This is a multi-line
         block quote with
         *rich text* **and**
         multiple lines.

         And with different paragraphs within the quote.

         Like this.

Tables
~~~~~~

.. rest-example::

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

Images
~~~~~~

.. rest-example::

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop
      :alt: Mountain landscape with snow-capped peaks

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop

   .. image:: _static/test-image.png

   .. image:: _static/camera.svg

Video
~~~~~

.. rest-example::

   .. video:: https://www.w3schools.com/html/mov_bbb.mp4

   .. video:: https://www.w3schools.com/html/mov_bbb.mp4
      :caption: Sample video demonstrating video support with a caption

   .. video:: _static/test-video.mp4
      :caption: Local test video file

Audio
~~~~~

.. rest-example::

   .. audio:: https://thetestdata.com/assets/audio/wav/thetestdata-sample-wav-2.wav

   .. audio:: _static/test-audio.wav

PDF
~~~

.. rest-example::

   .. pdf-include:: https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf

   .. pdf-include:: _static/test.pdf

Mathematical Equations
~~~~~~~~~~~~~~~~~~~~~~

The builder supports mathematical equations using the ``sphinx.ext.mathjax`` extension.

.. rest-example::

   You can include inline equations like this: :math:`E = mc^2` in your text.

   You can also include block-level equations:

   .. math::

      i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)

Rest Examples
~~~~~~~~~~~~~

The `sphinx-toolbox rest_example extension <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/rest_example.html>`_ allows you to show both the reStructuredText source code and its rendered output side by side.
This is useful for documentation that demonstrates how to write reStructuredText directives.

.. rest-example::

   .. rest-example::

      .. code-block:: python

         """Python code."""


         def greet(name: str) -> str:
             """Return a greeting message."""
             return f"Hello, {name}!"


         greet(name="World")

Embed Blocks
~~~~~~~~~~~~

Embed blocks can be created using the `sphinx-iframes <https://pypi.org/project/sphinx-iframes/>`_ extension.

.. iframe:: https://www.youtube.com/embed/dQw4w9WgXcQ

Sphinx ``toctree``\s are hidden
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. toctree::

      other

Line Blocks
~~~~~~~~~~~~

.. rest-example::

   The builder supports line blocks using pipe characters to preserve line breaks:

   Nothing in between

   |

   Now something in between

   | This is a line block
   | with multiple lines
   | preserved exactly as written
