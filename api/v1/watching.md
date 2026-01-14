# Watching API

This API tracks playback progress and watched/watchlist state.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/watching`

Get watching info for a specific item.

### Request

`GET /v1/watching?id=<itemId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching?id=123"
```

### Response


```json
{
  "status": 200,
  "item": {
    "id": 123,
    "status": -1,
    "title": "Some title",
    "type": "movie",
    "videos": [
      { "id": 52294, "number": 1, "title": "", "duration": 6388, "time": 0, "status": -1, "updated": null }
    ]
  }
}
```

Status values are API-defined (commonly `-1` = not watched, `0` = in progress, `1` = watched).

## GET `/v1/watching/movies`

List “continue watching” items for movie-like content.

### Request

`GET /v1/watching/movies`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching/movies"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 123,
      "title": "Some title",
      "type": "movie",
      "subtype": null,
      "posters": { "small": "https://...", "medium": "https://...", "big": "https://..." }
    }
  ]
}
```

## GET `/v1/watching/serials`

List series with new/unwatched episodes.

### Request

`GET /v1/watching/serials`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching/serials"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 123,
      "title": "Some series",
      "type": "serial",
      "subtype": null,
      "posters": { "small": "https://...", "medium": "https://...", "big": "https://..." },
      "new": 5,
      "total": 100,
      "watched": 42
    }
  ]
}
```

## GET `/v1/watching/marktime`

Mark playback time (progress sync). The client typically calls this endpoint every ~30 seconds during playback.

### Request

`GET /v1/watching/marktime?id=<itemId>&video=<videoId>&time=<seconds>&season=<optional>`

Query parameters:

- `id` (required int): item id
- `video` (required int): media/video id
- `time` (required int): playback position in seconds
- `season` (optional int): season number/id (API-defined; used for serials)

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching/marktime?id=123&video=1001&time=120&season=1"
```

### Response


```json
{
  "status": 200
}
```

Note: invalid `id`/`video` combinations may return errors like:

```json
{ "status": 404, "error": "Requested item or video not found." }
```

## GET `/v1/watching/toggle`

Toggle watched/unwatched state.

### Request

`GET /v1/watching/toggle?id=<itemId>&video=<optional>&season=<optional>`

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching/toggle?id=123&video=1001"
```

### Response


```json
{
  "status": 200,
  "watched": 0,
  "watching": { "status": -1 }
}
```

## GET `/v1/watching/togglewatchlist`

Toggle watchlist (subscribe/unsubscribe) for an item (commonly used for series).

### Request

`GET /v1/watching/togglewatchlist?id=<itemId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/watching/togglewatchlist?id=123"
```

### Response


```json
{
  "status": 200,
  "watching": true
}
```

