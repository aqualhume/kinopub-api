# API2 Items

Base URL: `https://cdn-service.space/`

These endpoints were documented based on responses captured by `tools/kinoapi_tests/run_tests.py` (local snapshots; do not commit/share).

## GET `/api2/v1.1/items/search`

Search items by text query.

### Request

`GET /api2/v1.1/items/search?q=<query>&page=<optional>&perpage=<optional>`

Example:

```bash
curl "https://cdn-service.space/api2/v1.1/items/search?q=terminator"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 104122,
      "type": "serial",
      "title": "Some title",
      "value": "Some title (2024)",
      "year": 2024,
      "voice": null,
      "plot": "Plot text",
      "poor_quality": false,
      "posters": {
        "small": "https://...",
        "medium": "https://...",
        "big": "https://...",
        "wide": "https://..."
      },
      "imdb": 14153236,
      "imdb_rating": 6.9,
      "kinopoisk": 4389432,
      "kinopoisk_rating": 6.4
    }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 40, "total_items": 40 }
}
```

## GET `/api2/v1.1/items/{id}`

Get basic item info by id.

### Request

`GET /api2/v1.1/items/{id}`

Example:

```bash
curl "https://cdn-service.space/api2/v1.1/items/104122"
```

### Response


```json
{
  "status": 200,
  "item": {
    "id": 104122,
    "title": "Some title",
    "age_rating": -1,
    "fps": 23.974,
    "imdb": 14153236,
    "imdb_rating": 6.9,
    "kinopoisk": 4389432,
    "kinopoisk_rating": 6.4
  }
}
```

## GET `/api2/v1.1/items/collections/{id}`

Get collections that contain the item.

### Request

`GET /api2/v1.1/items/collections/{id}`

Example:

```bash
curl "https://cdn-service.space/api2/v1.1/items/collections/104122"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 260,
      "title": "Collection title",
      "views": 3767,
      "watchers": 119,
      "created": 1469876785,
      "updated": 1725030623,
      "posters": {
        "small": "https://...",
        "medium": "https://...",
        "big": "https://..."
      }
    }
  ]
}
```

## GET `/api2/v1/backdrop/{id}`

Get a **wide/backdrop** artwork URL for an item (used as a fallback when `posters.wide` is missing).

### Request

`GET /api2/v1/backdrop/{id}?kp_id=<kp_id>`

- **id (path)**: IMDb numeric id (field `imdb` in API2 item objects).
- **kp_id (query)**: KinoPub item id (field `id` in API2 item objects). Despite the name, this is **not** the `kinopoisk` field.

Example:

```bash
curl "https://cdn-service.space/api2/v1/backdrop/14153236?kp_id=104122"
```

### Response

Returns a single URL string (the app expects it to start with `http`).

Example:

```json
"https://cdn-service.space/storage/backdrops/....jpg"
```
