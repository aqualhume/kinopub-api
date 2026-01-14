# TV API

Live TV channels.

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/tv`

Get the list of available TV channels.

### Request

`GET /v1/tv`

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/tv"
```

### Response


```json
{
  "status": 200,
  "channels": [
    {
      "id": 1,
      "title": "Channel title",
      "name": "channel_code",
      "logos": {
        "s": "https://.../logo_s.png",
        "m": "https://.../logo_m.png",
        "l": "https://.../logo_l.png"
      },
      "playlist": "",
      "embed": "",
      "current": "",
      "status": null,
      "stream": "https://.../playlist.m3u8"
    }
  ]
}
```

Field notes (observed):

- `channels[].logos.s` / `channels[].logos.m`: PNG logo URL. Observed size: **240×180** (often the same URL for both).
- `channels[].logos.l`: optional; not observed in current `/v1/tv` responses.
