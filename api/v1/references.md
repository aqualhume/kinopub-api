# References API

Static reference dictionaries used by the client (server locations, streaming types, etc.).

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/references/server-location`

List available server locations.

### Request

`GET /v1/references/server-location`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/references/server-location"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 1, "location": "de", "name": "Germany" }
  ]
}
```

## GET `/v1/references/streaming-type`

List available streaming types.

### Request

`GET /v1/references/streaming-type`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/references/streaming-type"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 1, "code": "hls4", "version": 4, "name": "HLS4", "description": "Description" }
  ]
}
```

## GET `/v1/references/voiceover-type`

List voiceover/dubbing types.

### Request

`GET /v1/references/voiceover-type`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/references/voiceover-type"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 1, "title": "Dubbing", "short_title": "DUB" }
  ]
}
```

## GET `/v1/references/voiceover-author`

List voiceover authors.

### Request

`GET /v1/references/voiceover-author`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/references/voiceover-author"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 1, "title": "VideoService", "short_title": null }
  ]
}
```

## GET `/v1/references/video-quality`

List available video quality options.

### Request

`GET /v1/references/video-quality`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/references/video-quality"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 1, "title": "480p", "quality": 480 },
    { "id": 2, "title": "720p", "quality": 720 }
  ]
}
```

Note:

- Use `id` values from this list for the `quality` filter in [`GET /v1/items`](content.md#get-v1items).

## GET `/v1/subtitles`

List available subtitles languages.

### Request

`GET /v1/subtitles`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/subtitles"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": "eng", "title": "English" }
  ]
}
```
