Changelog
=========

.. towncrier release notes start

2026.08.11
----------

- Add configurable ``diff`` and append-before-delete ``replace`` upload strategies
  to the upload API, command-line tool, and automatic Sphinx publishing.

- ``tab-set`` and ``tab-item`` directives (from the ``sphinx-design`` extension) now convert to Notion ``Tabs`` blocks, with each tab's label and content preserved, mirroring the existing ``sphinx-tabs`` support.

- Keep an existing page cover when its local cover file is unchanged.

- Delay page metadata changes until every upload cancellation check has passed.

- Allow direct page updates by ID without requiring an unused parent location.

- Preserve visible content inside compound directives.

- Render user-authored topic directives as callouts instead of aborting the build.

- Preserve figure legend paragraphs after the captioned image.

- Grid tables with rowspans or colspans now duplicate merged content across the covered Notion cells and emit a suppressible ``notion.unsupported_table`` warning, instead of shifting later cells.

- Local ``notion-file`` uploads now retain their configured display name as well as their caption.

- Omitting icon and cover options now preserves existing Notion page metadata instead of clearing editor-managed presentation.

- Ambiguous title-based uploads now stop with a stable error that directs users to ``--page-id`` instead of crashing with an assertion.

- Attributed block quotes and epigraphs now retain their author in a nested paragraph instead of aborting the Notion build.

- Native reStructuredText footnotes now render bracketed inline numbers and numbered body bullets, including auto-numbered, explicit, named, and repeated references.

- Native reStructuredText citations now render bracketed inline references and labeled bibliography bullets while preserving formatted citation bodies.

- Recognized document metadata such as authors, version, and date now renders as labeled bullets before the document body instead of being omitted.

- Custom reStructuredText field lists now render as bold labeled bullets with nested bodies, preserving field order, inline formatting, and multiple paragraphs.

- Native reStructuredText option lists now render as bulleted command options with nested descriptions, preserving aliases, arguments, and inline formatting.

- Images and figures with ``:target:`` now keep the target URL in the image caption and emit a suppressible ``notion.unsupported_image`` warning, instead of aborting the build.

- Nested line blocks now flatten into Notion paragraphs with two-space indentation per nesting level, preserved line boundaries, and inline formatting instead of aborting the build.

- Sphinx ``centered`` directives now render as normal Notion paragraphs with a suppressible ``notion.unsupported_layout`` warning, instead of aborting the build.

- Sphinx ``versionadded``, ``versionchanged``, and ``deprecated`` directives now render as Notion callouts with their generated labels, versions, inline formatting, and nested content preserved.

- Sphinx ``productionlist`` grammar directives now render as aligned plain-text Notion code blocks instead of aborting the build.

- Sphinx ``hlist`` directives now flatten into ordinary Notion bulleted items with a suppressible ``notion.unsupported_layout`` warning, instead of aborting the build.

- Standard ``:sub:`` and ``:sup:`` inline roles now render their content as plain Notion rich text, preserving nested formatting, instead of aborting the build.

- ``sphinx-tabs`` and ``sphinx-design`` are no longer installed automatically. They are not imported by ``sphinx_notion`` (their tabs are detected from the rendered output), so install them yourself alongside the other extensions you enable in ``conf.py`` if you use the ``tabs``/``tab`` or ``tab-set``/``tab-item`` directives.

2026.06.28
----------

- When a file upload to Notion fails, log the HTTP status and response body (with the filename of the failing asset) instead of discarding them. A non-JSON 403 is identified as a Cloudflare WAF block -- which Notion's upload endpoint sits behind -- with a hint that it is typically triggered by literal SQL or script text in the uploaded bytes, such as an SVG whose ``<text>`` contains ``CREATE TABLE ...``, and that rasterizing such diagrams to PNG avoids it.

- Level-4 section headings now convert to Notion ``heading_4`` blocks (newly supported by the Notion API) instead of raising an error. Headings at level 5 or deeper are still rejected with a clear message.

- ``tabs`` and ``tab`` directives (from the ``sphinx-tabs`` extension) now convert to Notion ``Tabs`` blocks, with each tab's label and content preserved. Tab labels are rendered as plain text.

2026.06.24.1
------------

- Upload all of a page's files before deleting any of its existing blocks, so that a file the Notion API rejects (for example an oversized image or an SVG with an external DTD) fails the publish with the live page left intact instead of emptied.

2026.06.24
----------

- Require ``ultimate-notion`` 0.9.10 or newer, which splits deeply-nested block trees reconstructed from serialized JSON into Notion-compliant requests on ``append()`` instead of sending an over-nested request that Notion rejects with a 400.

2026.06.23
----------

- Require ``ultimate-notion`` 0.9.9 or newer. It strips the read-only ``archived``/``in_trash``/``is_archived``/``has_children`` fields from nested blocks and accepts the ``in_trash`` field on file uploads, so the internal workaround for these is no longer needed and has been removed.

2026.06.09
----------

- Add a ``--page-id`` option to ``notion-upload`` (and a matching ``notion_page_id`` Sphinx configuration value) to update an existing page by ID instead of matching by title. The page is renamed to the given title, and the upload fails if no page with that ID exists, preventing a silent fork when a page is renamed.

2026.04.28
----------


2026.04.15
----------


2026.03.10.1
------------


2026.03.10
----------


2026.02.18
----------


2026.02.15
----------


2026.02.09.1
------------


- Add support for `sphinxcontrib-mermaid`_ diagrams.
- Add support for the ``notion-file`` directive for Notion File blocks.

2026.02.09
----------


- Render cross-references as plain text instead of silently dropping them, and emit a build warning.
- Add support for the ``glossary`` directive and ``:term:`` cross-references.

2026.01.11
----------


2026.01.08
----------


2026.01.03
----------

2025.12.23.1
------------

2025.12.23
----------

- Add support for rubric directives.

2025.12.21
----------

- Add support for the ``describe`` directive.
- Add support for definition lists.

2025.12.10.1
------------

2025.12.10
----------

2025.11.25
----------

2025.11.24
----------

2025.11.15.3
------------

2025.11.15.2
------------

2025.11.15.1
------------

2025.11.15
----------

2025.11.06
----------

2025.11.04.1
------------

2025.11.04
----------

2025.11.03.1
------------

2025.11.03
----------

2025.11.02
----------

2025.11.01
----------

2025.10.28
----------

2025.10.24.2
------------

2025.10.24.1
------------

2025.10.24
----------

2025.10.09
----------

2025.10.07.1
------------

2025.10.07
----------

2025.10.06
----------

2025.10.05.4
------------

2025.10.05.3
------------

2025.10.05.2
------------

2025.10.05.1
------------

2025.10.05
----------

2025.10.04.1
------------

2025.10.04
----------

2025.10.03
----------

2025.10.02.1
------------

2025.10.02
----------

2025.10.01.1
------------

2025.10.01
----------

2025.09.29
----------

2025.09.26
----------

2025.09.25.4
------------

2025.09.25.3
------------

2025.09.25.2
------------

2025.09.25.1
------------

2025.09.25
----------

2025.09.12.3
------------

2025.09.12.2
------------

2025.09.12.1
------------

2025.09.12
----------

2025.09.11
----------

2025.09.10
----------

2025.09.09
----------

2025.09.07
----------

2025.09.03
----------

2025.09.02
----------

2025.08.30
----------

2025.08.29
----------

2025.08.28
----------

2025.08.27.4
------------

2025.08.27.3
------------

2025.08.27.2
------------

2025.08.27.1
------------

2025.08.27
----------

2025.08.24.2
------------

2025.08.24.1
------------

2025.08.24
----------

2025.08.23.1
------------

2025.08.23
----------

2025.08.19.2
------------

2025.08.19.1
------------

2025.08.19
----------

.. _sphinxcontrib-mermaid: https://github.com/mgaitan/sphinxcontrib-mermaid
