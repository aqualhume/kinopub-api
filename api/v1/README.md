# KinoPub API v1.0

This folder contains an API reference for the KinoPub API

## Base URL

All endpoints below are relative to:

`https://api.service-kp.com/`

## Contents

- [`openapi.yaml`](openapi.yaml) — OpenAPI 3.0 (Swagger) spec generated from these markdown docs
- [`authentication.md`](authentication.md) — OAuth2 Device Flow, access/refresh tokens
- [`errors.md`](errors.md) — error response shapes and examples
- [`user.md`](user.md) — current user info
- [`device.md`](device.md) — devices, settings, notify/unlink/remove
- [`content.md`](content.md) — catalog (types/genres/countries), items, search, media links, trailer, vote, comments, shortcuts
- [`bookmarks.md`](bookmarks.md) — bookmark folders + item actions
- [`collections.md`](collections.md) — collections + collection items
- [`watching.md`](watching.md) — watching status + progress tracking
- [`history.md`](history.md) — watch history + clear history
- [`tv.md`](tv.md) — TV channels
- [`references.md`](references.md) — reference dictionaries (server locations, streaming types, etc.)

## Request basics (important)

### Authentication / `access_token`

Most endpoints require an access token. The API supports **two** ways to provide it:

- Preferred: `Authorization` header

  `Authorization: Bearer <access_token>`

- Alternative (legacy): `access_token` query parameter

  `?access_token=<access_token>`

For new integrations, prefer the `Authorization` header.

### POST body format (important)

Most non-OAuth POST endpoints in v1 use **form-encoded** bodies:

- Content-Type: `application/x-www-form-urlencoded`
- Body: key/value pairs (`field=value&field2=value2`)

Examples are included in each section file.

### Pagination

Many list endpoints support:

- `page` — page number (integer)
- `perpage` — items per page (integer)

When present, pagination is returned as an object named `pagination` with:

```json
{
  "total": 100,
  "current": 1,
  "perpage": 25,
  "total_items": 2500
}
```

Notes:

- `total_items` is optional (often present on list/search endpoints).
- `total_count` may also appear on some endpoints/older APIs (treated as optional).

### Time values

Most `created`, `updated`, `last_seen`, etc. fields are numeric timestamps returned by the API. Treat them as **Unix timestamps** unless noted otherwise.

## Response conventions

The API is not fully uniform; common patterns you will see:

- Many endpoints return wrapper objects with a `status` field (usually `200` on success)
- Some endpoints return **plain arrays** (e.g. `/v1/types`, `/v1/genres`, `/v1/countries`)
- OAuth endpoints return token payloads and/or OAuth error payloads
- For error payload examples and gotchas, see [`errors.md`](errors.md)

## Known gotchas

- Prefer `Authorization: Bearer <token>`; `?access_token=<token>` is also supported as a legacy option
- Most POST endpoints are form-encoded (not JSON)
- `/v1/history` response uses a `history` field (not `items`)
- `device.is_browser` is a boolean
- Device settings values are nested objects (`{label, value, type}`)
- `duration.average` is a floating point value
- OAuth token response may omit `token_type` (treat it as optional; default to `Bearer`)

