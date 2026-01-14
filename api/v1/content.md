# Content API

This section covers video content browsing/search and related endpoints.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## Poster sizes (observed)

When present, items include a `posters` object with URLs for different image variants.

Observed pixel sizes:

- `posters.small`: **165×250**
- `posters.medium`: **250×375**
- `posters.big`: **500×750**
- `posters.wide`: **not fixed** (background artwork). Observed: **1280×720**, **1920×1080**, **2800×1575**, **3840×2160**, and sometimes **1536×1024** or **2098×1381**.
- `seasons[].episodes[].thumbnail` (serial item details): **480×270** (URL often ends with `/480x270.jpg`).

## GET `/v1/types`

Get available **content types**.

### Request

`GET /v1/types`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/types"
```

### Response

Response wrapper:

```json
{
  "status": 200,
  "items": [
    { "id": "movie", "title": "Movies" },
    { "id": "serial", "title": "Series" }
  ]
}
```

## GET `/v1/genres`

Get available genres.

### Request

`GET /v1/genres?type=<optional>`

Query parameters:

- `type` (optional, string): genre group/type filter (API-defined)

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/genres"
```

### Response

Response wrapper:

```json
{
  "status": 200,
  "items": [
    { "id": 1, "title": "Comedy", "type": "movie" },
    { "id": 10, "title": "Disaster", "type": "docu" }
  ]
}
```

## GET `/v1/countries`

Get available countries.

### Request

`GET /v1/countries`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/countries"
```

### Response

Response wrapper:

```json
{
  "status": 200,
  "items": [
    { "id": 1, "title": "USA" },
    { "id": 2, "title": "UK" }
  ]
}
```

## GET `/v1/items`

List content items.

### Request

`GET /v1/items`

Query parameters (all optional):

- `type` (string): content type id (e.g. `movie`, `serial`)
- `genre` (string): one or more genre ids (commonly comma-separated, e.g. `1,2`)
- `country` (string): one or more country ids (commonly comma-separated, e.g. `1,2`)
- `year` (string): year filter (API-defined; often `YYYY` or `YYYY-YYYY`)
- `finished` (int): `0|1` (typically for series)
- `actor` (string): actor name(s)
- `director` (string): director name(s)
- `title` (string): title search/filter (API-defined)
- `letter` (string): first-letter filter
- `quality` (repeated int): quality id list (Retrofit list encoding results in `quality=1&quality=2`)
- `sort` (string): sorting (API-defined). Known values: `updated-`, `created-`, `rating-`, `views-`, `year-` (trailing `-` indicates descending).
- `conditions[]` (repeated string): advanced filter conditions (API-defined). Repeat the `conditions[]` key to pass multiple conditions. Known keys (observed in the official app and accepted by the API): `year`, `imdb_rating`, `kinopoisk_rating`, `created` (e.g. `conditions[]=year>=1900&conditions[]=imdb_rating>=7`).
- `page` (int): page number
- `perpage` (int): items per page

Notes:

- The official KinoPub app also sends additional/variable query parameters via a dynamic query map (`@QueryMap`). Keys vary by feature/client.

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items?type=movie&genre=1,2&sort=updated-&page=1&perpage=25"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 1,
      "title": "Title / Original title",
      "type": "movie",
      "subtype": "multi",
      "year": 2006,
      "cast": "Actor 1, Actor 2",
      "director": "Director 1",
      "voice": "Dub / Original",
      "duration": { "average": 2570.055, "total": 2570 },
      "langs": 2,
      "ac3": 0,
      "subtitles": 3,
      "quality": 1080,
      "genres": [{ "id": 1, "title": "Comedy", "type": "movie" }],
      "countries": [{ "id": 1, "title": "USA" }],
      "plot": "Plot text",
      "imdb": 123,
      "imdb_rating": 7.8,
      "imdb_votes": 10000,
      "kinopoisk": 456,
      "kinopoisk_rating": 7.5,
      "kinopoisk_votes": 9000,
      "rating": 10,
      "rating_votes": 187,
      "rating_percentage": 82,
      "views": 15,
      "comments": 5,
      "finished": false,
      "advert": false,
      "poor_quality": false,
      "created_at": 1704067200,
      "updated_at": 1704153600,
      "in_watchlist": false,
      "subscribed": false,
      "posters": { "small": "https://...", "medium": "https://...", "big": "https://...", "wide": "https://..." },
      "tracklist": [],
      "trailer": { "id": 123, "file": "/trailers/a/bc/123.mp4", "url": "https://..." }
    }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 25, "total_items": 1 }
}
```

Gotcha:

- `duration.average` can be a **floating point** value.

## GET `/v1/items/{id}`

Get item details, including seasons/episodes/videos.

### Request

`GET /v1/items/{id}?nolinks=<0|1>`

Query parameters:

- `nolinks` (optional int, default `1` in this client): when `1`, the API may omit heavy streaming link payloads in item details.

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/123?nolinks=1"
```

### Response


```json
{
  "status": 200,
  "item": {
    "id": 123,
    "title": "Some title",
    "type": "serial",
    "posters": { "small": "https://...", "medium": "https://...", "big": "https://...", "wide": "https://..." },
    "seasons": [
      {
        "id": 10,
        "number": 1,
        "title": "Season 1",
        "episodes": [
          {
            "id": 1001,
            "number": 1,
            "snumber": 1,
            "title": "Episode 1",
            "thumbnail": "https://...",
            "duration": 1234,
            "watched": 0,
            "tracks": 2,
            "watching": { "status": 0, "time": 120 }
          }
        ]
      }
    ]
  }
}
```

Notes:

- Movie-like content typically returns `item.videos`.
- Series-like content typically returns `item.seasons`.
- Watching state may appear via `watched` and `watching` fields.

## GET `/v1/items/search`

Search items by text query.

### Request

`GET /v1/items/search?q=<query>`

Query parameters:

- `q` (required, string): search query
- `type` (optional, string): content type filter
- `field` (optional, string): search field selector (API-defined)
- `page` (optional, int)
- `perpage` (optional, int)
- `sectioned` (optional, int): legacy behavior may change the response shape when set to `1`

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/search?q=terminator&perpage=25"
```

### Response


## GET `/v1/items/similar`

Get similar items for a given item id.

### Request

`GET /v1/items/similar?id=<itemId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/similar?id=123"
```

### Response


## GET `/v1/items/fresh`

Shortcut list (fresh content).

### Request

`GET /v1/items/fresh`

Query parameters (optional): `type`, `genre`, `page`, `perpage`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/fresh?type=movie&page=1&perpage=25"
```

### Response


## GET `/v1/items/hot`

Shortcut list (hot content).

### Request

`GET /v1/items/hot`

Query parameters (optional): `type`, `genre`, `page`, `perpage`

### Response


## GET `/v1/items/popular`

Shortcut list (popular content).

### Request

`GET /v1/items/popular`

Query parameters (optional): `type`, `genre`, `page`, `perpage`

### Response


## GET `/v1/items/media-links`

Get streaming file URLs + subtitles for a specific media id (`mid`).

This endpoint is used to fetch heavy link payloads (often omitted from `/v1/items/{id}` when `nolinks=1`).

### Request

`GET /v1/items/media-links?mid=<mediaId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/media-links?mid=456"
```

### Response


```json
{
  "id": 456,
  "thumbnail": "https://.../480x270.jpg",
  "files": [
    {
      "codec": "h264",
      "w": 1920,
      "h": 1080,
      "quality": "1080p",
      "quality_id": 3,
      "file": "/b/8c/diBAgF24FkaNBwPpB.mp4",
      "url": {
        "http": "https://host/token/file.mp4",
        "hls": "https://host/token/file.m3u8",
        "hls2": "https://host/token/file.m3u8",
        "hls4": "https://host/token/file.m3u8"
      }
    }
  ],
  "subtitles": [
    {
      "lang": "eng",
      "shift": 0,
      "embed": true,
      "forced": false,
      "file": "/a/71/29725.srt",
      "url": "https://host/token/file.srt"
    }
  ]
}
```

Notes:

- This success payload does **not** include a `status` field.
- Some video-file objects may use `url` or `urls`.

## GET `/v1/items/media-video-link`

Get a single playable URL for a file path and stream type.

### Request

`GET /v1/items/media-video-link?file=<path>&type=<type>`

Query parameters:

- `file` (required, string): file path (e.g. `/b/8c/diBAgF24FkaNBwPpB.mp4`)
- `type` (required, string): stream type (commonly `http`, `hls`, `hls2`, `hls4`)

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/media-video-link?file=%2Fb%2F8c%2FdiBAgF24FkaNBwPpB.mp4&type=hls4"
```

### Response


```json
{
  "url": "https://host/hls4/client/token/path/to/file.mp4?loc=de"
}
```

## GET `/v1/items/trailer`

Get trailer info for an item.

### Request

`GET /v1/items/trailer?id=<optional>&sid=<optional>`

Query parameters:

- `id` (optional int): item id
- `sid` (optional string): trailer id (API-defined)

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/trailer?id=123"
```

### Response


```json
{
  "status": 200,
  "trailer": [
    { "id": 123, "url": "https://cdn.example/hls/.../trailers/a/bc/123.mp4/master-v1a1.m3u8?loc=nl" }
  ]
}
```

## GET `/v1/items/vote`

Vote “like” or “dislike” for an item.

### Request

`GET /v1/items/vote?id=<itemId>&like=<0|1>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/vote?id=123&like=1"
```

### Response


```json
{
  "voted": true,
  "total": "5",
  "positive": "5",
  "negative": "0",
  "rating": 5
}
```

## GET `/v1/items/comments`

Get comments for an item.

### Request

`GET /v1/items/comments?id=<itemId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/items/comments?id=123"
```

### Response


```json
{
  "status": 200,
  "item": { "id": 123, "title": "Some title" },
  "comments": [
    {
      "id": 1,
      "depth": 0,
      "unread": false,
      "deleted": false,
      "message": "comment message",
      "created": 1704153600,
      "rating": "0",
      "user": { "id": 10, "name": "UserName", "avatar": "https://..." }
    }
  ]
}
```

Field notes (observed):

- `comments[].user.avatar`: avatar image URL. Observed (this account): **80×80** (gravatar default); may vary by provider/parameters.
