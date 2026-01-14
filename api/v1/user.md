# User API

Base URL: `https://api.service-kp.com/`

Authentication: use `Authorization: Bearer <access_token>` (preferred). Alternative (legacy): `?access_token=<access_token>`.

## GET `/v1/user`

Get information about the current user (profile + subscription).

### Request

`GET /v1/user`

Example:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://api.service-kp.com/v1/user"
```

### Response


```json
{
  "status": 200,
  "user": {
    "username": "someuser",
    "reg_date": 1567811381,
    "subscription": {
      "active": true,
      "end_time": 1704153600,
      "days": 12.5
    },
    "settings": {
      "show_erotic": true,
      "show_uncertain": false
    },
    "profile": {
      "name": "User Name",
      "avatar": "https://example.com/avatar.jpg"
    }
  }
}
```

Field notes:

- `user.username` (string): account username
- `user.reg_date` (int, optional): registration timestamp (seconds)
- `user.subscription.active` (boolean): whether subscription is active
- `user.subscription.end_time` (number, optional): subscription end timestamp
- `user.subscription.days` (number, optional): remaining days (may be fractional)
- `user.settings.show_erotic` / `user.settings.show_uncertain` (optional): user content filters
- `user.profile.name` (optional): profile display name
- `user.profile.avatar` (optional): avatar image URL. Observed (this account): **80×80** (gravatar default); may vary by provider/parameters.

