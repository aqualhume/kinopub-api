# Collections API

Collections are curated lists of items.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/collections`

List collections.

### Request

`GET /v1/collections?sort=<optional>&page=<optional>&perpage=<optional>`

Query parameters (all optional):

- `sort` (string): sorting (API-defined). Known values: `views-`, `watchers-`, `updated-`, `created-` (trailing `-` indicates descending).
- `page` (int): page number
- `perpage` (int): items per page

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/collections?sort=updated-&page=1&perpage=25"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 1,
      "title": "Top movies",
      "views": 1000,
      "watchers": 10,
      "count": 50,
      "posters": { "small": "https://...", "medium": "https://...", "big": "https://..." },
      "created": 1704067200,
      "updated": 1704153600
    }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 25 }
}
```

## GET `/v1/collections/view`

Get items inside a collection.

### Request

`GET /v1/collections/view?id=<collectionId>&page=<optional>&perpage=<optional>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/collections/view?id=1&page=1&perpage=25"
```

### Response


```json
{
  "status": 200,
  "collection": {
    "id": 1,
    "title": "Top movies",
    "views": 1000,
    "watchers": 10,
    "count": 50,
    "posters": { "small": "https://...", "medium": "https://...", "big": "https://..." },
    "created": 1704067200,
    "updated": 1704153600
  },
  "items": [
    { "id": 123, "title": "Some title", "type": "movie", "year": 2006 }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 25 }
}
```

Item objects - see [`content.md`](content.md#get-v1items)).

