Heading 1 with *bold*
=====================

.. contents::

.. toctree::

   other

Some text with a link to `Google <https://google.com>`_ and `<https://example.com>`_.

This is **bold** and *italic* and ``inline code``.

.. note::

   This is an important note that demonstrates the note admonition support.

   Some nested content:

   * First level item in note
   * Another first level item

     * Second level nested in note
     * Another second level item

       * Third level nested in note (deep!)
       * Another third level item

         * Fourth level nested in note (very deep!)
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

   from collections import deque
   from typing import Protocol


   class Limit(Protocol):
      limit_id: str

      def is_allowed(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> bool: ...

      def record_request(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> None: ...


   class RequestCountLimit:
      def __init__(
         self,
         limit_id: str,
         urls: list[str],
         max_requests: int,
         window_seconds: float,
      ) -> None:
         self.limit_id = limit_id
         self.urls = urls
         self.max_requests = max_requests
         self.window_seconds = window_seconds
         self.user_requests: dict[int, deque[float]] = {}

      def is_allowed(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> bool:
         del request_body
         if request_url not in self.urls:
               return True

         if user_id not in self.user_requests:
               self.user_requests[user_id] = deque()

         requests = self.user_requests[user_id]
         cutoff_time = request_timestamp - self.window_seconds

         while requests and requests[0] <= cutoff_time:
               requests.popleft()

         return len(requests) < self.max_requests

      def record_request(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> None:
         del request_body
         if request_url not in self.urls:
               return

         self.user_requests[user_id].append(request_timestamp)


   class BodySizeLimit:
      def __init__(
         self,
         limit_id: str,
         url: str,
         max_bytes: int,
         window_seconds: float,
      ) -> None:
         self.limit_id = limit_id
         self.url = url
         self.max_bytes = max_bytes
         self.window_seconds = window_seconds
         self.user_body_sizes: dict[int, deque[tuple[float, int]]] = {}

      def is_allowed(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> bool:
         if request_url != self.url:
               return True

         if user_id not in self.user_body_sizes:
               self.user_body_sizes[user_id] = deque()

         body_sizes = self.user_body_sizes[user_id]
         cutoff_time = request_timestamp - self.window_seconds

         while body_sizes and body_sizes[0][0] <= cutoff_time:
               body_sizes.popleft()

         current_total = sum(size for _, size in body_sizes)
         return current_total + len(request_body) <= self.max_bytes

      def record_request(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> None:
         if request_url != self.url:
               return

         self.user_body_sizes[user_id].append((request_timestamp, len(request_body)))


   class RateLimiter:
      def __init__(self) -> None:
         self._limits: list[Limit] = [
               RequestCountLimit(
                  limit_id="v1_60s",
                  urls=["/v1/completions.stream"],
                  max_requests=3,
                  window_seconds=60.0,
               ),
               RequestCountLimit(
                  limit_id="v1_v2_3600s",
                  urls=["/v1/completions.stream", "/v2/completions.stream"],
                  max_requests=7,
                  window_seconds=3600.0,
               ),
               BodySizeLimit(
                  limit_id="v1_body_60s",
                  url="/v1/completions.stream",
                  max_bytes=100,
                  window_seconds=60.0,
               ),
         ]

      def allow_request(
         self,
         *,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> list[str]:
         violated_limit_ids: list[str] = [
               limit.limit_id
               for limit in self._limits
               if not limit.is_allowed(
                  user_id=user_id,
                  request_url=request_url,
                  request_body=request_body,
                  request_timestamp=request_timestamp,
               )
         ]

         if violated_limit_ids:
               return violated_limit_ids

         for limit in self._limits:
               limit.record_request(
                  user_id=user_id,
                  request_url=request_url,
                  request_body=request_body,
                  request_timestamp=request_timestamp,
               )
         return []

   class BodySizeLimit:
      def __init__(
         self,
         limit_id: str,
         url: str,
         max_bytes: int,
         window_seconds: float,
      ) -> None:
         self.limit_id = limit_id
         self.url = url
         self.max_bytes = max_bytes
         self.window_seconds = window_seconds
         self.user_body_sizes: dict[int, deque[tuple[float, int]]] = {}

      def is_allowed(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> bool:
         if request_url != self.url:
               return True

         if user_id not in self.user_body_sizes:
               self.user_body_sizes[user_id] = deque()

         body_sizes = self.user_body_sizes[user_id]
         cutoff_time = request_timestamp - self.window_seconds

         while body_sizes and body_sizes[0][0] <= cutoff_time:
               body_sizes.popleft()

         current_total = sum(size for _, size in body_sizes)
         return current_total + len(request_body) <= self.max_bytes

      def record_request(
         self,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> None:
         if request_url != self.url:
               return

         self.user_body_sizes[user_id].append((request_timestamp, len(request_body)))


   class RateLimiter:
      def __init__(self) -> None:
         self._limits: list[Limit] = [
               RequestCountLimit(
                  limit_id="v1_60s",
                  urls=["/v1/completions.stream"],
                  max_requests=3,
                  window_seconds=60.0,
               ),
               RequestCountLimit(
                  limit_id="v1_v2_3600s",
                  urls=["/v1/completions.stream", "/v2/completions.stream"],
                  max_requests=7,
                  window_seconds=3600.0,
               ),
               BodySizeLimit(
                  limit_id="v1_body_60s",
                  url="/v1/completions.stream",
                  max_bytes=100,
                  window_seconds=60.0,
               ),
         ]

      def allow_request(
         self,
         *,
         user_id: int,
         request_url: str,
         request_body: bytes,
         request_timestamp: float,
      ) -> list[str]:
         violated_limit_ids: list[str] = [
               limit.limit_id
               for limit in self._limits
               if not limit.is_allowed(
                  user_id=user_id,
                  request_url=request_url,
                  request_body=request_body,
                  request_timestamp=request_timestamp,
               )
         ]

         if violated_limit_ids:
               return violated_limit_ids

         for limit in self._limits:
               limit.record_request(
                  user_id=user_id,
                  request_url=request_url,
                  request_body=request_body,
                  request_timestamp=request_timestamp,
               )
         return []


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
