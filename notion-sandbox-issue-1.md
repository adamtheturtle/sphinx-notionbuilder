# Page response example missing `type` field in properties

## Description

The page response example in the OpenAPI spec has properties that are missing the required `type` and `id` fields. This causes validation errors when using the mock responses with Notion API client libraries that have strict schema validation.

## Location in code

The `SimplePage` example is defined at:
https://github.com/naftiko/notion-sandbox/blob/96ffa0b6ad2761de4e43d0008c3f62b340cbed09/openapi/notion-openapi.yml#L7506-L7542

Specifically, the `properties.Name` section at lines 7527-7539:
https://github.com/naftiko/notion-sandbox/blob/96ffa0b6ad2761de4e43d0008c3f62b340cbed09/openapi/notion-openapi.yml#L7527-L7539

## Current format

```yaml
properties:
  Name:
    title:
      - type: text
        text:
          content: My Page Title
        plain_text: My Page Title
        annotations:
          bold: false
          # ...
```

## Expected format

According to the [Notion API documentation](https://developers.notion.com/reference/page), each property should include `id` and `type` fields:

```yaml
properties:
  Name:
    id: title
    type: title
    title:
      - type: text
        text:
          content: My Page Title
        plain_text: My Page Title
        annotations:
          bold: false
          # ...
```

## Impact

Client libraries like [ultimate-notion](https://github.com/ultimate-notion/ultimate-notion) use Pydantic models with strict validation. The missing `type` field causes validation errors:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Page
properties.Name
  Value error, Missing 'type' in data {'title': [...]}
```

This prevents using Microcks with notion-sandbox for integration testing against these libraries.
