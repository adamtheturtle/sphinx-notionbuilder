Suppressed Warnings Sample
==========================

This sample demonstrates features that produce warnings with the Notion builder.
The warnings are suppressed via ``suppress_warnings`` in ``conf.py``.

Cross-references
~~~~~~~~~~~~~~~~

.. rest-example::

   A reference to a label: :ref:`other-doc-label`.

   A reference to a document: :doc:`other`.

   A download reference: :download:`example.txt <_static/example.txt>`.

Glossary term references
~~~~~~~~~~~~~~~~~~~~~~~~

.. glossary::

   sample term
      A sample glossary term used to demonstrate :term: cross-references.

.. rest-example::

   A reference to a glossary term: :term:`sample term`.

Autosummary
~~~~~~~~~~~

.. rest-example::

   .. autosummary::
      :nosignatures:

      example_module.greet



Subscript and Superscript
~~~~~~~~~~~~~~~~~~~~~~~~~

Standard ``:sub:`` and ``:sup:`` roles render as plain text because Notion rich
text has no vertical-position annotation. The builder emits a suppressible
``notion.unsupported_inline`` warning.

.. rest-example::

   Water is H\ :sub:`2`\ O and the area is x\ :sup:`2`.

Horizontal Lists
~~~~~~~~~~~~~~~~

Multi-column horizontal lists cannot be represented in Notion, so items are
flattened into a single bulleted list with a suppressible
``notion.unsupported_layout`` warning.

.. rest-example::

   .. hlist::
      :columns: 2

      * One
      * Two
      * Three
      * Four


.. toctree::

   other
