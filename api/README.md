# KinoPub API Documentation

This directory contains documentation for the KinoPub API. 

Upstream docs site: [kinoapi.com](https://kinoapi.com/index.html)

## Contents

### Endpoint Documentation (`v1`)
Detailed documentation for each API endpoint category:
- [authentication.md](v1/authentication.md) - OAuth2 device flow authentication
- [content.md](v1/content.md) - Video items, search, catalog
- [watching.md](v1/watching.md) - Progress tracking, watch status
- [bookmarks.md](v1/bookmarks.md) - User folders and saved items
- [collections.md](v1/collections.md) - Curated collections
- [history.md](v1/history.md) - Watch history
- [device.md](v1/device.md) - Device management and settings
- [user.md](v1/user.md) - User profile and subscription
- [tv.md](v1/tv.md) - Live TV channels
- [references.md](v1/references.md) - Static reference data
- [errors.md](v1/errors.md) - Error codes and responses

### API2 Documentation (`v1.1`)
Separate docs/spec for the `v1.1/*` endpoints (different base URL):

- [README.md](v1.1/README.md)
- [items.md](v1.1/items.md)
- [openapi.yaml](v1.1/openapi.yaml)

## Base URL

```
https://api.service-kp.com/
```

v1.1 base URL:

```
https://cdn-service.space/
```

## Authentication

The API uses OAuth2 device flow. All authenticated endpoints require a Bearer token:

```
Authorization: Bearer <access_token>
```

## OAuth client credentials (`client_id` / `client_secret`)

To start the OAuth2 **device flow** (`POST /oauth2/device?grant_type=device_code`) you need:

- `client_id`
- `client_secret`

Known `client_id` values seen in the wild (secrets intentionally omitted):

- `android`
- `xbmc`

For security (and to avoid publishing working credentials), this repository **does not include client secrets**.
Use your own credentials (or credentials you are authorized to use) and keep them private.

If you use the helper scripts in `tools/kinoapi_tests/`, provide credentials via environment variables:

- `KINOPUB_CLIENT_ID`
- `KINOPUB_CLIENT_SECRET`

Or pass them directly to `tools/kinoapi_tests/extract_token.py` using `--client-id` / `--client-secret`.
