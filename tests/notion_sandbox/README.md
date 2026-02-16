# Notion OpenAPI Fixture

`notion-openapi.yml` is a compact OpenAPI contract used by
`tests/test_upload_mock_api.py`.

The test uploads this contract into a local Microcks instance, then points
`ultimate_notion.Session` at the generated mock endpoints to exercise the
upload synchronization flow without talking to the real Notion API.

Why this file exists:

- It keeps the mock contract local to the tests.
- It avoids requiring external network access to a live Notion workspace.
- It includes a local workaround for
  `naftiko/notion-sandbox#4`: `SimplePage.properties.Name` includes `id` and
  `type`.
