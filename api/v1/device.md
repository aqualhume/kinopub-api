# Device API

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/device`

List devices linked to the account.

### Request

`GET /v1/device`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device"
```

### Response


```json
{
  "status": 200,
  "devices": [
    {
      "id": 1,
      "title": "Living Room TV",
      "hardware": "AndroidTV/1.0",
      "software": "Android/13",
      "created": 1704067200,
      "updated": 1704153600,
      "last_seen": 1704153600,
      "is_browser": false,
      "settings": {
        "supportSsl": { "label": "Use SSL", "value": true, "type": "bool" },
        "supportHevc": { "label": "HEVC", "value": true, "type": "bool" },
        "supportHdr": { "label": "HDR", "value": false, "type": "bool" },
        "support4k": { "label": "4K", "value": false, "type": "bool" },
        "mixedPlaylist": { "label": "Mixed playlist", "value": 1, "type": "bool" },
        "streamingType": {
          "label": "Streaming type",
          "type": "list",
          "value": [
            { "id": 1, "label": "HTTP", "description": "", "selected": 0 },
            { "id": 4, "label": "HLS4", "description": "", "selected": 1 }
          ]
        },
        "serverLocation": {
          "label": "Server location",
          "type": "list",
          "value": [
            { "id": 1, "label": "Netherlands", "description": "", "selected": 1 }
          ]
        }
      }
    }
  ]
}
```

Gotchas:

- `is_browser` is a **boolean** (not `0/1`).
- `settings.*` entries are objects (`{label, value, type}`), not plain values.

## GET `/v1/device/info`

Get info for the **current** device.

### Request

`GET /v1/device/info`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/info"
```

### Response


```json
{
  "status": 200,
  "device": {
    "id": 1,
    "title": "Living Room TV",
    "hardware": "AndroidTV/1.0",
    "software": "Android/13",
    "created": 1704067200,
    "updated": 1704153600,
    "last_seen": 1704153600,
    "is_browser": false,
    "settings": {
      "supportSsl": { "label": "Use SSL", "value": true, "type": "bool" }
    }
  }
}
```

## GET `/v1/device/{id}`

Get info for a specific device by id.

### Request

`GET /v1/device/{id}`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/123"
```

### Response


## GET `/v1/device/{id}/settings`

Get device settings as a key/value map.

### Request

`GET /v1/device/{id}/settings`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/123/settings"
```

### Response


```json
{
  "status": 200,
  "settings": {
    "supportSsl": { "label": "Use SSL", "value": 1, "type": "bool" },
    "supportHevc": { "label": "HEVC", "value": 1, "type": "bool" },
    "serverLocation": {
      "label": "Server location",
      "type": "list",
      "value": [
        { "id": 1, "label": "Netherlands", "description": "", "selected": 1 },
        { "id": 3, "label": "Russia", "description": "", "selected": 0 }
      ]
    },
    "streamingType": {
      "label": "Streaming type",
      "type": "list",
      "value": [
        { "id": 1, "label": "HTTP", "description": "HTTP pseudo streaming", "selected": 0 },
        { "id": 4, "label": "HLS4", "description": "", "selected": 1 }
      ]
    }
  }
}
```

Notes:

- Each setting value uses the `{label, value, type}` wrapper.
- For `type: "list"`, `value` is usually an **array** of options; the currently chosen option is marked by `selected` (commonly `1|0`).
- Some APIs return device settings embedded inside `device.settings` using a fixed set of keys.

## POST `/v1/device/{id}/settings`

Update device settings.

### Request

`POST /v1/device/{id}/settings`

Body: **form-encoded** (`application/x-www-form-urlencoded`)

Fields (all required by this client’s interface):

- `supportSsl` (int): `0|1`
- `supportHevc` (int): `0|1`
- `supportHdr` (int): `0|1`
- `support4k` (int): `0|1`
- `mixedPlaylist` (int): `0|1`
- `streamingType` (int): id from [`GET /v1/references/streaming-type`](references.md#get-v1referencesstreaming-type)
- `serverLocation` (int): id from [`GET /v1/references/server-location`](references.md#get-v1referencesserver-location)

Example:

```bash
curl -X POST "https://api.service-kp.com/v1/device/123/settings" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "supportSsl=1&supportHevc=1&supportHdr=0&support4k=0&mixedPlaylist=0&streamingType=1&serverLocation=1"
```

### Response


```json
{
  "status": 200
}
```

## POST `/v1/device/notify`

Register/update the current device info (recommended after authentication and on app start).

### Request

`POST /v1/device/notify`

Body: **form-encoded**

Fields:

- `title` (string): device name shown to the user
- `hardware` (string): device hardware info
- `software` (string): device software/OS info

Example:

```bash
curl -X POST "https://api.service-kp.com/v1/device/notify" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "title=KinoPub&hardware=Pixel_8&software=Android_15"
```

### Response


```json
{
  "status": 200
}
```

## POST `/v1/device/unlink`

Unlink the **current** device (effectively logs out this device).

### Request

`POST /v1/device/unlink`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/unlink"
```

### Response


```json
{
  "status": 200
}
```

## POST `/v1/device/remove`

Remove a device by id (query parameter).

### Request

`POST /v1/device/remove?id=<deviceId>`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/remove?id=123"
```

### Response


```json
{
  "status": 200,
  "current": false
}
```

## POST `/v1/device/{id}/remove`

Remove a device by id (path parameter).

### Request

`POST /v1/device/{id}/remove`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/device/123/remove"
```

### Response


