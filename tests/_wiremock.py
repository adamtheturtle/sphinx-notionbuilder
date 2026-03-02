"""WireMock test helpers."""

import respx
from beartype import beartype


@beartype
def count_mock_requests(
    *,
    mock: respx.MockRouter,
    method: str,
    url_path: str,
) -> int:
    """Count matching requests captured by the respx mock."""
    return sum(
        1
        for call in mock.calls  # pyright: ignore[reportUnknownVariableType]
        if call.request.method == method  # pyright: ignore[reportUnknownMemberType]
        and call.request.url.path == url_path  # pyright: ignore[reportUnknownMemberType]
    )
