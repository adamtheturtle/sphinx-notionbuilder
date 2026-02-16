# Database retrieval and query endpoints for parent_database_id flow

## Summary

The upload logic supports creating pages inside a Notion database
(`parent_database_id`), but the sandbox has no endpoints for database retrieval
or querying.

## Current behavior

The sandbox defines endpoints for pages and blocks but has no database-related
paths.

## Expected behavior

Add endpoints for:

### `GET /v1/databases/{database_id}`

Retrieve a database object, e.g.:

```yaml
/v1/databases/{database_id}:
  get:
    operationId: retrieveDatabase
    responses:
      '200':
        description: Database
        content:
          application/json:
            examples:
              Success:
                value:
                  object: database
                  id: <database-uuid>
                  title:
                    - type: text
                      text:
                        content: "Test Database"
                      plain_text: "Test Database"
                  properties:
                    Name:
                      id: title
                      type: title
                      title: {}
```

### `POST /v1/databases/{database_id}/query`

Query database pages, e.g.:

```yaml
/v1/databases/{database_id}/query:
  post:
    operationId: queryDatabase
    responses:
      '200':
        description: Query results
        content:
          application/json:
            examples:
              Success:
                value:
                  object: list
                  type: page
                  page: {}
                  has_more: false
                  results: []
```

## Why this matters

The upload function accepts either `parent_page_id` or `parent_database_id`.
The database parent path calls `session.get_db()` and
`parent.get_all_pages().to_pages()`, which require these endpoints. Without
them, the database parent flow cannot be integration-tested.

## Official reference

- [Retrieve a database](https://developers.notion.com/reference/retrieve-a-database)
- [Query a database](https://developers.notion.com/reference/post-database-query)
