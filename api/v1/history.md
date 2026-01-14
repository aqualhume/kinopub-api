# History API

Watch history endpoints.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/history`

Get watch history entries.

### Request

`GET /v1/history?page=<optional>&perpage=<optional>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/history?page=1&perpage=25"
```

### Response


```json
{
  "status": 200,
  "history": [
    {
      "counter": 1,
      "first_seen": 1704067200,
      "last_seen": 1704153600,
      "time": 3600,
      "deleted": false,
      "item": {
        "id": 123,
        "title": "Movie Title",
        "type": "movie",
        "subtype": "",
        "year": 2006,
        "created_at": 1704067200,
        "updated_at": 1704153600,
        "poor_quality": false,
        "rating": 10,
        "rating_votes": 187,
        "rating_percentage": 82,
        "posters": { "small": "https://...", "medium": "https://...", "big": "https://...", "wide": "https://..." },
        "trailer": { "id": 123, "file": "/trailers/a/bc/123.mp4", "url": "https://..." }
      },
      "media": {
        "id": 456,
        "number": 1,
        "title": "Episode Title",
        "snumber": 0,
        "thumbnail": "https://...",
        "duration": 1234,
        "tracks": 2,
        "subtitles": [
          { "lang": "eng", "file": "/1/2/3.srt", "embed": false, "forced": false, "shift": 0 }
        ]
      }
    }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 25, "total_items": 1 }
}
```

Important:

- The list field is named **`history`** (not `items`).

## POST `/v1/history/clear-for-media`

Clear history for a specific media/episode/video.

### Request

`POST /v1/history/clear-for-media?id=<mediaId>`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/history/clear-for-media?id=456"
```

### Response

The API returns HTTP `200` with a JSON `null` body:

```json
null
```

## POST `/v1/history/clear-for-season`

Clear history for a season.

### Request

`POST /v1/history/clear-for-season?id=<seasonId>`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/history/clear-for-season?id=10"
```

### Response

The API returns HTTP `200` with a JSON `null` body.

## POST `/v1/history/clear-for-item`

Clear history for an item (movie/series).

### Request

`POST /v1/history/clear-for-item?id=<itemId>`

```bash
curl -X POST -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/history/clear-for-item?id=123"
```

### Response

The API returns HTTP `200` with a JSON `null` body.

