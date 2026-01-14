# Authentication (OAuth2 Device Flow)

The KinoPub API uses an OAuth2 **Device Flow** (device code + polling) to obtain an `access_token` and `refresh_token`.

Base URL: `https://api.service-kp.com/`

After you obtain an `access_token`, pass it to API v1 calls using the **preferred** method:

- `Authorization: Bearer <access_token>`

Alternative (legacy):

- `?access_token=<access_token>`

## Step 1 — Get `device_code`

### Request

`POST /oauth2/device`

Query parameters:

- `grant_type` (required): `device_code`
- `client_id` (required): your client id
- `client_secret` (required): your client secret

Example:

```bash
curl -X POST "https://api.service-kp.com/oauth2/device?grant_type=device_code&client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

### Response


```json
{
  "code": "ab23lcdefg340g0jgfgji45jb",
  "user_code": "ASDFGH",
  "verification_uri": "https://kino.pub/device",
  "expires_in": 8600,
  "interval": 5
}
```

- `code`: device code used for polling
- `user_code`: short code to show the user
- `verification_uri`: where the user should enter `user_code`
- `expires_in`: seconds until this device code expires
- `interval`: minimum polling interval (seconds)

## Step 2 — Poll for `access_token`

Poll **no more often** than `interval` seconds.

### Request

`POST /oauth2/device`

Query parameters:

- `grant_type` (required): `device_token`
- `client_id` (required)
- `client_secret` (required)
- `code` (required): the `code` from step 1

Example:

```bash
curl -X POST "https://api.service-kp.com/oauth2/device?grant_type=device_token&client_id=YOUR_ID&client_secret=YOUR_SECRET&code=ab23lcdefg340g0jgfgji45jb"
```

### Response (pending)

You may receive HTTP `400` with an OAuth error payload:


```json
{
  "error": "authorization_pending",
  "error_description": "Optional text"
}
```

### Response (success)


```json
{
  "access_token": "asdfghjkl123456789",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "qwertyu12345678",
  "scope": null
}
```

Notes:

- The API may omit `token_type` — treat it as **optional** and default to `Bearer`.
- After obtaining a token, it’s recommended to call [`POST /v1/device/notify`](device.md#post-v1devicenotify) to register/update device info.

## Step 3 — Refresh `access_token`

When the access token expires, request a new one using the refresh token.

### Request

`POST /oauth2/device`

Query parameters:

- `grant_type` (required): `refresh_token`
- `client_id` (required)
- `client_secret` (required)
- `refresh_token` (required)

Example:

```bash
curl -X POST "https://api.service-kp.com/oauth2/device?grant_type=refresh_token&client_id=YOUR_ID&client_secret=YOUR_SECRET&refresh_token=YOUR_REFRESH_TOKEN"
```

### Response


```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "NEW_REFRESH_TOKEN",
  "scope": null
}
```

