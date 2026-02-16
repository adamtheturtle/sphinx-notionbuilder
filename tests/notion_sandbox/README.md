# Notion OpenAPI Fixture

`notion-openapi.yml` is based on
[notion-sandbox](https://github.com/naftiko/notion-sandbox), an OpenAPI contract
for the Notion API. It is trimmed to the subset used by `sphinx_notion._upload`
and includes local workarounds for upstream issues.

The file is loaded into a local [Microcks](https://microcks.io/) instance by
`tests/test_upload_mock_api.py` so the upload synchronization flow can be
exercised without talking to the real Notion API.

## How to update

Edit `notion-openapi.yml` directly. When you need to cover a new Notion endpoint
or response shape, add the path and example responses by hand, following the
patterns already in the file and the
[Notion API reference](https://developers.notion.com/reference).

## Local workarounds

The file includes workarounds for issues in the upstream
[notion-sandbox](https://github.com/naftiko/notion-sandbox) project:

- `naftiko/notion-sandbox#4` &mdash; `SimplePage.properties.Name` includes the
  required `id` and `type` fields that the upstream sandbox omits.
- The `/v1/comments` endpoint uses `x-microcks-operation: dispatcher: FALLBACK`
  to avoid Microcks switching to `URI_PARAMS` dispatching when query parameters
  are defined.
