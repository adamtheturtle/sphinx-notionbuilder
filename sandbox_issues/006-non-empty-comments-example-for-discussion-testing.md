# Non-empty comments example for discussion testing

## Summary

The `GET /v1/comments` endpoint only provides an example with an empty
`results` array. To test the `DiscussionsExistError` code path, the sandbox
needs an example (or a dispatcher-based variant) that returns comments.

## Current behavior

The single example returns:

```yaml
results: []
```

## Expected behavior

Provide an additional example with non-empty results, e.g.:

```yaml
results:
  - object: comment
    id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    parent:
      type: block_id
      block_id: c02fc1d3-db8b-45c5-a222-27595b15aea7
    discussion_id: 11111111-2222-3333-4444-555555555555
    created_time: '2023-03-01T10:00:00.000Z'
    last_edited_time: '2023-03-01T10:00:00.000Z'
    created_by:
      object: user
      id: 71e95936-2737-4e11-b03d-f174f6f13e90
    rich_text:
      - type: text
        text:
          content: "Review comment on this block"
        plain_text: "Review comment on this block"
        annotations:
          bold: false
          italic: false
          strikethrough: false
          underline: false
          code: false
          color: default
```

Ideally, the dispatcher could return different examples based on the `block_id`
query parameter, so some blocks appear to have discussions while others do not.

## Why this matters

The upload logic checks `block.discussions` for every block it plans to delete.
When `cancel_on_discussion=True` and discussions exist, it raises
`DiscussionsExistError`. This error path cannot be tested with the current
always-empty comments response.

## Official reference

- [List comments](https://developers.notion.com/reference/get-comments)
- [Comment object](https://developers.notion.com/reference/comment-object)
