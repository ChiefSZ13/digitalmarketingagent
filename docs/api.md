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

Returns HTTP 201 with a `PerceptionRun`. When persistence is enabled, the
response includes `analysis_run_id`, a UUID that can be used with the persisted
analysis routes.

The response includes `marketplace_snapshot`. In the current schema, marketplace
provider candidates are normalized and validated before aggregation. Important
fields include:

- `product_identity`: canonical identity used for matching.
- `validated_listings`: every normalized candidate plus its match result.
- `validation_summary`: exact, probable, uncertain, rejected, alternate-package,
  alternate-variant, and alternate-condition counts.
- `platform_rankings`: rankings built only from eligible primary matches.
- `price_estimates`: landed-price ranges built only from eligible primary
  matches.

Rejected and uncertain listings are represented in `validated_listings`, but
they are not included in primary rankings or price ranges.

## `GET /api/v1/perception-runs/{run_id}`

Returns a saved run. With `PERSISTENCE_ENABLED=false`, this is the local JSON
artifact repository. With `PERSISTENCE_ENABLED=true`, this is reconstructed from
the PostgreSQL report snapshot plus latest manual overrides.

## Persisted Analysis Routes

These routes require `PERSISTENCE_ENABLED=true`:

- `GET /api/v1/analyses`: list previous analyses with `limit`, `offset`,
  `status`, `product_id`, `search`, `created_after`, `created_before`, and
  `sort`.
- `GET /api/v1/analyses/{analysis_id}`: return summary, normalized rows,
  provider runs, latest overrides, and full report.
- `GET /api/v1/analyses/{analysis_id}/report`: export the full
  `PerceptionRun` JSON report.
- `GET /api/v1/analyses/{analysis_id}/marketplace`: return the persisted
  marketplace snapshot.
- `GET /api/v1/analyses/{analysis_id}/keywords`: return keyword candidates and
  keyword intelligence.
- `POST /api/v1/analyses/{analysis_id}/marketplace/{observation_id}/override`:
  append a manual review decision for a persisted marketplace observation.
- `GET /api/v1/analyses/{analysis_id}/marketplace/{observation_id}/overrides`:
  list override audit records for that observation.

The existing `POST /api/v1/perception-runs/{run_id}/marketplace-overrides`
continues to work by listing ID for the current report UI.

## Admin Database Inspector

The read-only inspector is available only when both `PERSISTENCE_ENABLED=true`
and `ADMIN_DB_INSPECTOR_ENABLED=true`:

- `GET /admin/db/tables`
- `GET /admin/db/tables/{table_name}?limit=25&offset=0&search=...`
- `GET /admin/db/tables/{table_name}/{record_id}`

Only declared ORM tables are inspectable. Secret-like fields are redacted.

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
