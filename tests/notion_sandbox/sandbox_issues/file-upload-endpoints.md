# File upload endpoints

The sandbox needs file upload endpoints so tests can exercise cover image uploads
and file-block uploads.

## Endpoints needed

- `POST /v1/file_uploads` — create a file upload session
- `POST /v1/file_uploads/{file_upload_id}/send` — send file data
- `GET /v1/file_uploads/{file_upload_id}` — retrieve upload status (polling)

## Notion API reference

- https://developers.notion.com/reference/file-uploads-intro
- https://developers.notion.com/reference/create-a-file-upload
- https://developers.notion.com/reference/send-file-upload
- https://developers.notion.com/reference/retrieve-a-file-upload
