# Typed list responses omit type-specific object key (`block`, `comment`)

## Summary

List responses that declare a specific `type` (for example `block` or
`comment`) omit the matching type-specific object key in examples.

For strict clients, this can cause parsing failures.

## Current behavior

Examples for endpoints such as:

- `GET /blocks/{block_id}/children` (`type: block`)
- `GET /comments` (`type: comment`)

include `type`, `results`, `has_more`, and `next_cursor`, but do not include
the companion key that Notion list payloads typically expose (for example
`block: {}` or `comment: {}`).

## Expected behavior

When `type` is present in list payloads, include the corresponding companion
object key in examples, e.g.:

```yaml
object: list
type: block
block: {}
has_more: false
next_cursor: null
results: []
```

and:

```yaml
object: list
type: comment
comment: {}
has_more: false
next_cursor: null
results: []
```

## Why this matters

Some typed Notion clients validate list envelopes using `type` plus the
matching type object field. Without the field, mock responses can be rejected
even though the endpoint and business logic are otherwise correct.

## Official reference

The official Notion API docs show this list-envelope pattern in endpoint
examples:

- [Retrieve block children](https://developers.notion.com/reference/get-block-children)
- [List comments](https://developers.notion.com/reference/get-comments)

## Scope note

This request is specifically about response examples matching the strict Notion
payload shape for better SDK compatibility.
