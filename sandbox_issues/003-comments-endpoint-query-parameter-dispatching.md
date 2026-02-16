# Comments endpoint returns 400 when query parameters are present

## Summary

`GET /v1/comments?block_id=...&page_size=100` returns a 400 error from
Microcks when query parameters are included. Without query parameters, the
endpoint responds correctly.

## Current behavior

When the Notion SDK calls the comments endpoint with query parameters:

```
GET /v1/comments?block_id=c02fc1d3-db8b-45c5-a222-27595b15aea7&page_size=100
```

Microcks returns:

```
400 - The response ?block_id=c02fc1d3-...?page_size=100 does not exist!
```

This happens because Microcks switches to `URI_PARAMS` dispatching when query
parameters are defined in the OpenAPI spec, and it cannot match the parameter
values to any example name.

## Expected behavior

The comments endpoint should return the example response regardless of which
query parameter values are sent.

## Workaround

Adding the `x-microcks-operation` extension to override the dispatcher:

```yaml
/v1/comments:
  get:
    operationId: listComments
    x-microcks-operation:
      dispatcher: FALLBACK
```

## Why this matters

The Notion API's `GET /v1/comments` endpoint requires `block_id` as a query
parameter. Any test that needs to check block discussions will hit this
endpoint. Without the workaround, all discussion-related test flows fail.

## Scope note

This may be a general Microcks behavior rather than a notion-sandbox issue
specifically. If the sandbox project already uses `x-microcks-operation`
extensions elsewhere, this could be documented as the expected pattern.
