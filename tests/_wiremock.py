"""WireMock test helpers."""

import requests
from beartype import beartype


@beartype
def count_wiremock_requests(
    *,
    base_url: str,
    method: str,
    url_path: str,
) -> int:
    """Count matching requests captured by WireMock."""
    payload = {
        "method": method,
        "urlPath": url_path,
    }
    response = requests.post(
        url=f"{base_url}/__admin/requests/count",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    count = response.json()["count"]
    assert isinstance(count, int)
    return count
