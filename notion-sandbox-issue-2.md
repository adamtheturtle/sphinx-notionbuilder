# Version mismatch between info.version and server URL

## Description

There's a version mismatch in the OpenAPI spec between `info.version` and the server URL path.

## Location in code

- `info.version` at line 6: https://github.com/naftiko/notion-sandbox/blob/96ffa0b6ad2761de4e43d0008c3f62b340cbed09/openapi/notion-openapi.yml#L6
- Server URL at line 15: https://github.com/naftiko/notion-sandbox/blob/96ffa0b6ad2761de4e43d0008c3f62b340cbed09/openapi/notion-openapi.yml#L15

## Details

- `info.version`: `1.1.0` (line 6)
- Server URL: `http://localhost:8080/rest/notion-api/1.1.4` (line 15)

## Impact

When using Microcks to serve mocks from this spec, it uses `info.title` and `info.version` to construct the mock URL path:

```
/rest/{info.title}/{info.version}/...
```

This results in:
```
/rest/notion-api/1.1.0/...
```

But the server URL in the spec suggests the version should be `1.1.4`, which could cause confusion about which version the spec represents.

## Suggestion

Either:
1. Update `info.version` to `1.1.4` to match the server URL, or
2. Update the server URL to use `1.1.0` to match `info.version`
