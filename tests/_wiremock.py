"""WireMock test helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beartype import beartype

if TYPE_CHECKING:
    import respx
    from respx.models import Call


@beartype
def count_mock_requests(
    *,
    mock: respx.MockRouter,
    method: str,
    url_path: str,
) -> int:
    """Count matching requests captured by the respx mock."""
    calls: list[Call] = list(mock.calls)
    count = 0
    for call in calls:
        if call.request.method == method and call.request.url.path == url_path:
            count += 1
    return count


@beartype
def count_page_metadata_clear_requests(
    *,
    mock: respx.MockRouter,
    page_id: str,
) -> int:
    """Count page updates that explicitly clear icon or cover metadata."""
    page_paths = {
        f"/v1/pages/{page_id}",
        f"/v1/pages/{page_id.replace('-', '')}",
    }
    count = 0
    calls: list[Call] = list(mock.calls)
    for call in calls:
        if (
            call.request.method == "PATCH"
            and call.request.url.path in page_paths
        ):
            payload: dict[str, object] = json.loads(s=call.request.content)
            if (
                payload.get("icon", object()) is None
                or payload.get("cover", object()) is None
            ):
                count += 1
    return count
