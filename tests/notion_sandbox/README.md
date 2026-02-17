# Notion OpenAPI Fixture

`notion-openapi.yml` is based on
[notion-sandbox](https://github.com/naftiko/notion-sandbox), an OpenAPI contract
for the Notion API. It is trimmed to the subset used by `sphinx_notion._upload`
and includes local workarounds for upstream issues.

`notion-wiremock-stubs.json` is generated from `notion-openapi.yml` and used
when upload tests run against a local WireMock container.

`tests/test_upload_mock_api.py` loads these fixtures into a local WireMock
server so the upload synchronization flow can be exercised without talking to
the real Notion API.

## How to update

Edit `notion-openapi.yml` directly. When you need to cover a new Notion
endpoint or response shape, add the path and example responses by hand,
following the patterns already in the file and the
[Notion API reference](https://developers.notion.com/reference).

After editing the OpenAPI fixture, regenerate WireMock mappings:

```bash
uv run --extra=dev python tests/notion_sandbox/openapi_to_wiremock.py
```

Run upload tests:

```bash
uv run --extra=dev pytest tests/test_upload_mock_api.py
```

## Local workarounds

The file includes workarounds for issues in the upstream
[notion-sandbox](https://github.com/naftiko/notion-sandbox) project:

- `naftiko/notion-sandbox#4` &mdash; `SimplePage.properties.Name` includes the
  required `id` and `type` fields that the upstream sandbox omits.
