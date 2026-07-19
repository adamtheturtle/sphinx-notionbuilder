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


Table Cell Spans
~~~~~~~~~~~~~~~~

Notion tables do not support merged cells, so rowspans and colspans are
flattened by duplicating content with a suppressible
``notion.unsupported_table`` warning.

.. rest-example::

   +---+---+
   | A | B |
   +===+===+
   | merged|
   +---+---+

   +---+---+
   | A | B |
   +===+===+
   | X | Y |
   +   +---+
   |   | Z |
   +---+---+

.. toctree::

   other
