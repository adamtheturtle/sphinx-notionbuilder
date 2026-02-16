# SimplePage example is missing `Name.id` and `Name.type` metadata

## Summary

The `SimplePage` example omits required Notion page property metadata under
`properties.Name`:

- `id`
- `type`

This breaks strict API clients that validate page property objects using the
official Notion shape.

## Current behavior

In `components.examples.SimplePage`, `properties.Name` only contains `title`.
Strict clients fail to parse this example payload because a title property is
expected to include `id` and `type`.

## Expected behavior

`SimplePage` should include:

```yaml
properties:
  Name:
    id: title
    type: title
    title:
      - type: text
        text:
          content: My Page Title
```

## Why this matters

Consumers using typed SDKs (for example `ultimate-notion`) can fail during
deserialization when mock responses omit these fields, which blocks integration
tests against the sandbox.

## Additional context

This appears to already be tracked as:

- https://github.com/naftiko/notion-sandbox/issues/4

If helpful, this can be added there as extra reproduction detail instead of
opening a duplicate issue.
