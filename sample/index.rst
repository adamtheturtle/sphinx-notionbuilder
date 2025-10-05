Heading 1 with *bold*
=====================

.. contents::

.. toctree::

   other

.. rest-example::

   .. This is a comment that demonstrates comment support.
      Comments should not appear in the final output.

.. rest-example::

   Some text with a link to `Google <https://google.com>`_ and `<https://example.com>`_.

   This is **bold** and *italic* and ``inline code``.

   This text has :strike:`strike` formatting and :del:`deleted text` as well.

Colored Text
~~~~~~~~~~~~

The builder supports colored text using `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_:

.. rest-example::

   This is :text-red:`red text`, :text-blue:`blue text`, :text-green:`green text`, :text-yellow:`yellow text`, :text-orange:`orange text`, :text-purple:`purple text`, :text-pink:`pink text`, :text-brown:`brown text`, and :text-gray:`gray text`.

Background Colors
~~~~~~~~~~~~~~~~~~

The builder also supports background colors using `sphinxcontrib-text-styles <https://sphinxcontrib-text-styles.readthedocs.io/>`_:

.. rest-example::

   This is :bg-red:`red background text`, :bg-blue:`blue background text`, :bg-green:`green background text`, :bg-yellow:`yellow background text`, :bg-orange:`orange background text`, :bg-purple:`purple background text`, :bg-pink:`pink background text`, :bg-brown:`brown background text`, and :bg-gray:`gray background text`.

Other Text Styles
~~~~~~~~~~~~~~~~~~

.. rest-example::

   The builder supports additional text styles: :text-bold:`bold text`, :text-italic:`italic text`, :text-mono:`monospace text`, :text-strike:`strikethrough text`, and :text-underline:`underlined text`.

Keyboard Shortcuts
~~~~~~~~~~~~~~~~~~

.. rest-example::

   The builder supports keyboard shortcuts using the standard ``:kbd:`` role: Press :kbd:`Ctrl+C` to copy, :kbd:`Ctrl+V` to paste, and :kbd:`Ctrl+Z` to undo.

.. rest-example::

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

.. rest-example::

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


.. rest-example::

   .. tip::

      This is a helpful tip that demonstrates the tip admonition support.

.. rest-example::

   .. attention::

      This is an attention admonition that requires your attention.

.. rest-example::

   .. caution::

      This is a caution admonition that warns about potential issues.

.. rest-example::

   .. danger::

      This is a danger admonition that indicates a dangerous situation.

.. rest-example::

   .. error::

      This is an error admonition that shows error information.

.. rest-example::

   .. hint::

      This is a hint admonition that provides helpful hints.

.. rest-example::

   .. important::

      This is an important admonition that highlights important information.

.. rest-example::

   .. admonition:: Custom Admonition Title

      This is a generic admonition with a custom title. You can use this for
      any type of callout that doesn't fit the standard admonition types.

      It supports all the same features:

      * Bullet points
      * **Bold text** and *italic text*
      * ``Code snippets``

.. rest-example::

   .. collapse:: Click to expand this section

      This content is hidden by default and can be expanded by clicking the toggle.

      It supports **all the same formatting** as regular content.

      .. note::

         You can even nest admonitions inside collapsible sections!

.. rest-example::

   Here's an example of including a file:

   .. literalinclude:: conf.py
      :language: python

   And with a caption:

   .. literalinclude:: conf.py
      :language: python
      :caption: Example **Configuration** File

Nested Content in Bullet Lists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This demonstrates the new support for nesting various content types within bullet lists:

.. rest-example::

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

The builder supports numbered lists:

.. rest-example::

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


Heading with *italic* and ``inline code``
-----------------------------------------

The builder supports block quotes:

.. rest-example::

   Regular paragraph.

      This is a multi-line
      block quote with
      multiple lines.


Table Example
-------------

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

List Table with Stub (Header) Column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. rest-example::

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

.. rest-example::

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop

Image with Alt Text
~~~~~~~~~~~~~~~~~~~

.. rest-example::

.. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop
   :alt: Mountain landscape with snow-capped peaks

Image with Alt Text
~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop
      :alt: Beautiful mountain scenery

Local Image Example
~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. image:: _static/test-image.png
      :alt: Local test image

SVG support
~~~~~~~~~~~

.. rest-example::

   .. image:: _static/camera.svg

Video Examples
--------------

Simple Video
~~~~~~~~~~~~

.. rest-example::

   .. video:: https://www.w3schools.com/html/mov_bbb.mp4

Video with Caption
~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. video:: https://www.w3schools.com/html/mov_bbb.mp4
      :caption: Sample video demonstrating video support

Local Video Example
~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. video:: _static/test-video.mp4
      :caption: Local test video file

Audio Examples
--------------

Simple Audio
~~~~~~~~~~~~

.. rest-example::

   .. audio:: https://thetestdata.com/assets/audio/wav/thetestdata-sample-wav-2.wav

Local Audio Example
~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. audio:: _static/test-audio.wav

PDF Support
~~~~~~~~~~~~

Simple PDF
~~~~~~~~~~

.. rest-example::

   .. pdf-include:: https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf

Local PDF Example
~~~~~~~~~~~~~~~~~

.. rest-example::

   .. pdf-include:: _static/test.pdf

Mathematical Equations
~~~~~~~~~~~~~~~~~~~~~~

The builder supports mathematical equations using the ``sphinx.ext.mathjax`` extension.

Inline Equations
~~~~~~~~~~~~~~~~

.. rest-example::

   You can include inline equations like this: :math:`E = mc^2` in your text.

   Here are some more examples:

   * The quadratic formula: :math:`x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}`
   * The integral of x squared: :math:`\int x^2 dx = \frac{x^3}{3} + C`
   * Euler's identity: :math:`e^{i\pi} + 1 = 0`

Block Equations
~~~~~~~~~~~~~~~

You can also include block-level equations:

.. rest-example::

   .. math::

      E = mc^2

   The Schrödinger equation:

   .. math::

      i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)
