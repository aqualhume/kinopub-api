# Bookmarks API

Bookmarks represent user-defined folders containing saved items.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/bookmarks`

List bookmark folders.

### Request

`GET /v1/bookmarks`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/bookmarks"
```

### Response


```json
{
  "status": 200,
  "items": [
    {
      "id": 1,
      "title": "Family",
      "views": 10,
      "count": 23,
      "created": 1704067200,
      "updated": 1704153600
    }
  ]
}
```

## GET `/v1/bookmarks/{id}`

List items in a specific bookmark folder.

### Request

`GET /v1/bookmarks/{id}?page=<optional>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/bookmarks/1?page=1"
```

### Response


```json
{
  "status": 200,
  "items": [
    { "id": 123, "title": "Some title", "type": "movie", "year": 2006 }
  ],
  "pagination": { "total": 1, "current": 1, "perpage": 25 }
}
```

Item objects - see [`content.md`](content.md#get-v1items).

## GET `/v1/bookmarks/get-item-folders`

Get folders that currently contain a given item.

### Request

`GET /v1/bookmarks/get-item-folders?item=<itemId>`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/bookmarks/get-item-folders?item=123"
```

### Response


```json
{
  "status": 200,
  "folders": [
    {
      "id": 1,
      "user_id": 462634,
      "title": "Family",
      "views": 10,
      "count": 23,
      "created": 1704067200,
      "updated": 1704153600,
      "created_at": 1704067200,
      "updated_at": 1704153600
    }
  ]
}
```

## POST `/v1/bookmarks/create`

Create a new bookmark folder.

### Request

`POST /v1/bookmarks/create`

Body: **form-encoded**

Fields:

- `title` (string, required): folder name

```bash
curl -X POST "https://api.service-kp.com/v1/bookmarks/create" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "title=MyFolder"
```

### Response


```json
{
  "status": 200,
  "folder": {
    "id": 134,
    "title": "MyFolder",
    "views": 0,
    "count": 0,
    "created": 1704067200,
    "updated": 1704067200
  }
}
```

## POST `/v1/bookmarks/add`

Add an item to a folder.

### Request

`POST /v1/bookmarks/add`

Body: **form-encoded**

Fields:

- `item` (int, required): item id
- `folder` (int, required): folder id

```bash
curl -X POST "https://api.service-kp.com/v1/bookmarks/add" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "item=123&folder=1"
```

### Response


```json
{
  "status": 200,
  "exists": true
}
```

Note: `exists` is optional and may indicate whether the item already existed in the folder.

## POST `/v1/bookmarks/remove-item`

Remove an item from a folder.

### Request

`POST /v1/bookmarks/remove-item`

Body: **form-encoded**

Fields:

- `item` (int, required): item id
- `folder` (int, required): folder id

```bash
curl -X POST "https://api.service-kp.com/v1/bookmarks/remove-item" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "item=123&folder=1"
```

### Response


```json
{
  "status": 200
}
```

## POST `/v1/bookmarks/remove-folder`

Delete a bookmark folder.

### Request

`POST /v1/bookmarks/remove-folder`

Body: **form-encoded**

Fields:

- `folder` (int, required): folder id

```bash
curl -X POST "https://api.service-kp.com/v1/bookmarks/remove-folder" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "folder=1"
```

### Response


```json
{
  "status": 200
}
```

