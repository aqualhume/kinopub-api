# Errors

This section describes how the KinoPub API reports errors.

## General behavior

- The API typically returns errors with HTTP status codes **4xx** or **5xx**.
- For **valid API endpoints**, the response body is usually JSON.
- If you call a **wrong base URL / wrong path** (e.g. a missing `/api/` prefix on some hosts, or a completely unknown route), the server may return an **HTML** error page instead of JSON.

## Common JSON error shapes

### Unauthorized / invalid token

If you call an authenticated endpoint with a missing/invalid token, the API returns:

- HTTP `401`
- JSON body:

```json
{
  "status": 401,
  "error": "unauthorized"
}
```

This was verified against `https://api.service-kp.com/v1/user` and `https://cdn-service.space/api/v1/user`.

### OAuth errors (device flow)

OAuth endpoints (see [`authentication.md`](authentication.md)) use standard OAuth-style errors, for example:

```json
{
  "error": "authorization_pending",
  "error_description": "Optional text"
}
```

## Legacy documentation note

The old KinoAPI docs (for example `docs/kinoapi/site/www.kinoapi.com/_sources/errors.rst.txt`) show an older error payload like:

```json
{
  "name": "Unauthorized",
  "message": "You are requesting with an invalid credential.",
  "code": 0,
  "status": 401
}
```

In our live testing of the current API used by this project, the common `401` payload is the simpler `{status, error}` form shown above.

