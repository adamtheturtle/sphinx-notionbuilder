Suppressed Warnings Sample
==========================

This sample demonstrates cross-reference features that produce warnings with the Notion builder.
The warnings are suppressed via ``suppress_warnings = ["ref.notion"]`` in ``conf.py``.

Cross-references
~~~~~~~~~~~~~~~~

A reference to a label: :ref:`other-doc-label`.

A reference to a document: :doc:`other`.

A download reference: :download:`example.txt <_static/example.txt>`.

Autosummary
~~~~~~~~~~~

.. autosummary::
   :nosignatures:

   example_module.greet

.. toctree::

   other
