# listChildren examples with child_page and child_database block types

## Summary

The `GET /v1/blocks/{block_id}/children` endpoint examples only return
`paragraph` blocks. To test error handling for pages that contain subpages or
inline databases, the sandbox needs examples that include `child_page` and
`child_database` block types.

## Current behavior

The `listChildren` example always returns:

```yaml
results:
  - object: block
    type: paragraph
    ...
```

## Expected behavior

Provide additional examples (or a configurable variant) that return blocks with
`type: child_page` and `type: child_database`, e.g.:

```yaml
results:
  - object: block
    id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    type: child_page
    child_page:
      title: "Nested Page"
    has_children: false
    archived: false
    in_trash: false
```

and:

```yaml
results:
  - object: block
    id: aaaaaaaa-bbbb-cccc-dddd-ffffffffffff
    type: child_database
    child_database:
      title: "Inline Database"
    has_children: false
    archived: false
    in_trash: false
```

## Why this matters

The upload logic raises `PageHasSubpagesError` when a page has child pages and
`PageHasDatabasesError` when it has inline databases. These error paths cannot
be integration-tested without mock responses that include these block types.

## Official reference

- [Block object: child_page](https://developers.notion.com/reference/block#child-page)
- [Block object: child_database](https://developers.notion.com/reference/block#child-database)
