"""WireMock test helpers."""

from __future__ import annotations

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
