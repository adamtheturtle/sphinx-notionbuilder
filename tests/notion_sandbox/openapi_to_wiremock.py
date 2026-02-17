"""Generate WireMock mappings from the local Notion OpenAPI fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

JSONValue = (
    str
    | int
    | float
    | bool
    | None
    | dict[str, "JSONValue"]
    | list["JSONValue"]
)

_HTTP_METHODS = ("get", "post", "patch", "put", "delete")


def _pick_response(
    responses: dict[str, JSONValue],
) -> tuple[int, JSONValue]:
    """Pick a JSON response body from an OpenAPI responses object."""
    # Prefer success responses.
    response_codes = sorted(
        responses,
        key=lambda code: (
            0 if code.startswith("2") else 1,
            code,
        ),
    )
    for code in response_codes:
        response_value = responses.get(code, {})
        if not isinstance(response_value, dict):
            continue
        content_value = response_value.get("content", {})
        if not isinstance(content_value, dict):
            continue
        json_content_value = content_value.get("application/json", {})
        if not isinstance(json_content_value, dict):
            continue
        examples_value = json_content_value.get("examples")
        if isinstance(examples_value, dict) and examples_value:
            first_example = next(iter(examples_value.values()))
            if isinstance(first_example, dict):
                return int(code), first_example.get("value")
        if "example" in json_content_value:
            return int(code), json_content_value["example"]
        return int(code), None
    message = "No usable JSON response found in operation responses."
    raise RuntimeError(message)


def _build_mappings(openapi: dict[str, JSONValue]) -> list[dict[str, Any]]:
    """Convert OpenAPI paths into WireMock mappings."""
    paths_value = openapi.get("paths", {})
    if not isinstance(paths_value, dict):
        message = "OpenAPI document has no valid 'paths' object."
        raise TypeError(message)

    mappings: list[dict[str, Any]] = []
    for path, path_item_value in paths_value.items():
        if not isinstance(path_item_value, dict):
            continue
        for method in _HTTP_METHODS:
            operation_value = path_item_value.get(method)
            if not isinstance(operation_value, dict):
                continue
            responses_value = operation_value.get("responses", {})
            if not isinstance(responses_value, dict):
                continue
            status_code, body = _pick_response(responses=responses_value)
            operation_id_value = operation_value.get("operationId")
            name = (
                str(object=operation_id_value)
                if isinstance(operation_id_value, str)
                else f"{method.upper()} {path}"
            )
            response: dict[str, Any] = {
                "status": status_code,
                "headers": {"Content-Type": "application/json"},
            }
            if body is not None:
                response["jsonBody"] = body
            mappings.append(
                {
                    "name": name,
                    "request": {
                        "method": method.upper(),
                        "urlPath": path,
                    },
                    "response": response,
                    "persistent": True,
                },
            )

    return mappings


def _build_additional_mappings() -> list[dict[str, Any]]:
    """Return hand-authored mappings not representable in OpenAPI examples."""
    return [
        {
            "name": "listCommentsWithDiscussion",
            "priority": 1,
            "request": {
                "method": "GET",
                "urlPath": "/v1/comments",
                "queryParameters": {
                    "block_id": {
                        "equalTo": ("cccc0000-0000-0000-0000-000000000010")
                    }
                },
            },
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "object": "list",
                    "type": "comment",
                    "comment": {},
                    "has_more": False,
                    "results": [
                        {
                            "object": "comment",
                            "id": "c0de0000-0000-0000-0000-000000000001",
                            "parent": {
                                "type": "block_id",
                                "block_id": (
                                    "cccc0000-0000-0000-0000-000000000010"
                                ),
                            },
                            "discussion_id": (
                                "c0de0000-0000-0000-0000-000000000001"
                            ),
                            "rich_text": [],
                            "display_name": {
                                "type": "user",
                                "resolved_name": "Mock User",
                            },
                            "created_time": "2023-03-01T12:00:00.000Z",
                            "last_edited_time": "2023-03-01T12:00:00.000Z",
                            "created_by": {
                                "object": "user",
                                "id": "71e95936-2737-4e11-b03d-f174f6f13e90",
                            },
                        }
                    ],
                },
            },
            "persistent": True,
        }
    ]


def main() -> None:
    """Generate `notion-wiremock-stubs.json` next to this script."""
    sandbox_dir = Path(__file__).resolve().parent
    openapi_path = sandbox_dir / "notion-openapi.yml"
    output_path = sandbox_dir / "notion-wiremock-stubs.json"

    with openapi_path.open(encoding="utf-8") as openapi_file:
        openapi_obj: object = yaml.safe_load(  # type: ignore[no-untyped-call]
            stream=openapi_file
        )
    if not isinstance(openapi_obj, dict):
        message = "OpenAPI document is not a mapping."
        raise TypeError(message)
    openapi = cast("dict[str, JSONValue]", openapi_obj)

    mappings = _build_additional_mappings() + _build_mappings(openapi=openapi)
    with output_path.open(mode="w", encoding="utf-8") as output_file:
        json.dump(obj={"mappings": mappings}, fp=output_file, indent=2)
        output_file.write("\n")


if __name__ == "__main__":
    main()
