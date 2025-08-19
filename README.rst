|Build Status| |codecov| |PyPI|

Notion Builder for Sphinx
=========================

Extension for Sphinx which enables publishing documentation to Notion.

.. contents::

Installation
------------

``sphinx-notionbuilder`` is compatible with Python |minimum-python-version|\+.

.. code-block:: console

   $ pip install sphinx-notionbuilder

Add the following to ``conf.py`` to enable the extension:

.. code-block:: python

   """Configuration for Sphinx."""

   extensions = ["sphinx_notionbuilder"]

Supported features
------------------

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-notionbuilder/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-notionbuilder/actions
.. |codecov| image:: https://codecov.io/gh/adamtheturtle/sphinx-notionbuilder/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/adamtheturtle/sphinx-notionbuilder
.. |PyPI| image:: https://badge.fury.io/py/Sphinx-Notion-Builder.svg
   :target: https://badge.fury.io/py/Sphinx-Notion-Builder
.. |minimum-python-version| replace:: 3.13
