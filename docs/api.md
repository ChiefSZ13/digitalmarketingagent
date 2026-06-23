# API

Base path: `/api/v1`.

## `GET /health`

Returns `{"status":"ok"}`.

## `GET /ready`

Returns `{"status":"ready"}`.

## `POST /api/v1/perception-runs`

Multipart form fields:

- `images`: one to five JPG, PNG, or WebP files
- `description`: required nonempty text
- `brand`: optional
- `market`: optional
- `language`: optional
- `category_hint`: optional
- `target_audience_hint`: optional
- `include_debug`: optional, default false

Returns HTTP 201 with a `PerceptionRun`.

## `GET /api/v1/perception-runs/{run_id}`

Returns a saved local JSON artifact if present.

## Errors

Errors use RFC 7807-style fields:

```json
{
  "type": "https://example.local/errors/invalid-image",
  "title": "Invalid image",
  "status": 422,
  "detail": "Image 2 exceeds the configured size limit.",
  "instance": "/api/v1/perception-runs",
  "request_id": "req_..."
}
```

The app maps unsupported media to 415, oversized payloads to 413, invalid request data to 422, provider failures to 502, and unexpected failures to 500 without stack traces.

