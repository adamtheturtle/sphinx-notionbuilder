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


Linked Images
~~~~~~~~~~~~~

Notion images are not clickable, so ``:target:`` URLs are preserved in the
caption with a suppressible ``notion.unsupported_image`` warning.

.. rest-example::

   .. image:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop
      :target: https://example.com/full-size.png

   .. figure:: https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop
      :target: https://example.com/full-size.png

      Diagram *caption*.

.. toctree::

   other
