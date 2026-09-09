"""WireMock test helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beartype import beartype
from beartype.door import TypeHint
from typing_extensions import TypeIs

if TYPE_CHECKING:
    import respx
    from respx.models import Call

type JSONValue = (
    bool | int | float | str | list[JSONValue] | dict[str, JSONValue] | None
)


def _is_json_object(value: object, /) -> TypeIs[dict[str, JSONValue]]:
    """Return whether a decoded value is a string-keyed object."""
    return TypeHint(hint=dict[str, JSONValue]).is_bearable(obj=value)


def json_object(value: object, /) -> dict[str, JSONValue]:
    """Return a runtime-validated decoded JSON object."""
    assert _is_json_object(value)
    return value


def _is_json_array(value: object, /) -> TypeIs[list[JSONValue]]:
    """Return whether a decoded value is an array."""
    return TypeHint(hint=list[JSONValue]).is_bearable(obj=value)


def json_array(value: object, /) -> list[JSONValue]:
    """Return a runtime-validated decoded JSON array."""
    assert _is_json_array(value)
    return value


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
            payload = json_object(json.loads(s=call.request.content))
            if (
                payload.get("icon", object()) is None
                or payload.get("cover", object()) is None
            ):
                count += 1
    return count
