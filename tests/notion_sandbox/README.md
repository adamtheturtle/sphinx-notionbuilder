# Notion WireMock Fixture

`notion-wiremock-stubs.json` contains the WireMock mappings used by upload
tests.

`tests/test_upload_mock_api.py` loads these fixtures into a local WireMock
server so the upload synchronization flow can be exercised without talking to
the real Notion API.

## How to update

Edit `notion-wiremock-stubs.json` directly. When adding a new endpoint or
response shape, follow existing mapping patterns and the
[Notion API reference](https://developers.notion.com/reference).

Run upload tests:

```bash
uv run --extra=dev pytest tests/test_upload_mock_api.py
```
