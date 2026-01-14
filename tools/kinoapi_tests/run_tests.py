import argparse
import datetime as _dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


BASE_URL_DEFAULT = "https://api.service-kp.com/"
ENV_ACCESS_TOKEN = "KINOPUB_ACCESS_TOKEN"


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _is_json_content_type(headers: Dict[str, str]) -> bool:
    ct = headers.get("Content-Type", "")
    return "application/json" in ct or "application/js" in ct or "+json" in ct


def _safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_json(path: str, obj: Any) -> None:
    _write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def _redact_tokens(text: str) -> str:
    # Redact Bearer tokens and query params if they ever appear.
    text = re.sub(r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+", "Authorization: Bearer <REDACTED>", text)
    text = re.sub(r"access_token=[A-Za-z0-9._~+/=-]+", "access_token=<REDACTED>", text)
    return text


_SENSITIVE_JSON_KEYS = {
    # OAuth / auth
    "access_token",
    "refresh_token",
    "client_secret",
    "device_token",
    # Device flow codes
    "code",
    "user_code",
}


def _redact_json(obj: Any) -> Any:
    """
    Best-effort redaction of obviously sensitive fields in JSON snapshots.
    Note: snapshots can still contain personal account data; don't commit/share them.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        out: Dict[Any, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in _SENSITIVE_JSON_KEYS:
                out[k] = "<REDACTED>"
            else:
                out[k] = _redact_json(v)
        return out
    if isinstance(obj, list):
        return [_redact_json(x) for x in obj]
    return obj


def _ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else (url + "/")


def _derive_api2_base_url(v1_base_url: str) -> str:
    """
    Official KinoPub app uses:
      - v1: https://cdn-service.space/api/  (paths: v1/...)
      - api2: https://cdn-service.space/   (paths: api2/v1.1/..., api2/v1/...)

    If v1_base_url ends with '/api/' (or '/api'), derive the api2 base by stripping that segment.
    Otherwise, reuse v1_base_url.
    """
    if v1_base_url.endswith("/api/"):
        return _ensure_trailing_slash(v1_base_url[:-4])
    if v1_base_url.endswith("/api"):
        return _ensure_trailing_slash(v1_base_url[:-3])
    return _ensure_trailing_slash(v1_base_url)


# ---------------- Auth / token helpers ----------------


def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _default_token_file() -> str:
    return os.path.join(_script_dir(), ".local", "access_token.txt")


def _read_token_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return None
    except Exception:
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Allow JSON: {"access_token": "..."} or {"token": "..."}
    if raw.lstrip().startswith("{"):
        try:
            obj = json.loads(raw)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            t = obj.get("access_token") or obj.get("token")
            if isinstance(t, str) and t.strip():
                return t.strip()

    # Default: first non-empty, non-comment line.
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return None


def _resolve_access_token(token_arg: Optional[str], token_file: str) -> Tuple[Optional[str], str]:
    if token_arg and token_arg.strip():
        return token_arg.strip(), "arg"
    env_tok = os.environ.get(ENV_ACCESS_TOKEN)
    if env_tok and env_tok.strip():
        return env_tok.strip(), "env"
    file_tok = _read_token_file(token_file)
    if file_tok:
        return file_tok, "file"
    return None, "missing"


# ---------------- HTTP helpers ----------------


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    raw_text: str
    json: Optional[Any]


def _http_request(
    base_url: str,
    method: str,
    path: str,
    token: Optional[str],
    query: Optional[Dict[str, Any]] = None,
    form: Optional[Dict[str, Any]] = None,
    body: Optional[bytes] = None,
    body_content_type: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    timeout_s: int = 30,
) -> HttpResponse:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)

    if form is not None and body is not None:
        raise ValueError("Provide either form=... or body=..., not both.")

    data: Optional[bytes] = None
    headers: Dict[str, str] = {}

    headers["Accept"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if form is not None:
        data = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = body
        if body_content_type:
            headers["Content-Type"] = body_content_type

    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, method=method.upper(), headers=headers)

    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout_s) as resp:
            raw = resp.read()
            status = resp.status
            resp_headers = {k: v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
        resp_headers = {k: v for k, v in e.headers.items()}

    raw_text = raw.decode("utf-8", errors="replace")
    parsed_json: Optional[Any] = None
    if raw_text:
        is_jsonish = _is_json_content_type(resp_headers) or raw_text.lstrip().startswith(("{", "["))
        if is_jsonish:
            try:
                parsed_json = json.loads(raw_text)
            except Exception:
                parsed_json = None

    return HttpResponse(status=status, headers=resp_headers, raw_text=raw_text, json=parsed_json)


# ---------------- Validation helpers (shape-based) ----------------


def _type_name(x: Any) -> str:
    return type(x).__name__


def _require(cond: bool, msg: str, errors: List[str]) -> None:
    if not cond:
        errors.append(msg)


def _expect_obj(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, dict), f"{where}: expected object, got {_type_name(x)}", errors)


def _expect_list(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, list), f"{where}: expected array, got {_type_name(x)}", errors)


def _expect_str(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, str), f"{where}: expected string, got {_type_name(x)}", errors)


def _expect_int(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, int) and not isinstance(x, bool), f"{where}: expected int, got {_type_name(x)}", errors)


def _expect_bool(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, bool), f"{where}: expected bool, got {_type_name(x)}", errors)


def _expect_num(x: Any, where: str, errors: List[str]) -> None:
    _require(isinstance(x, (int, float)) and not isinstance(x, bool), f"{where}: expected number, got {_type_name(x)}", errors)


def _get(obj: dict, key: str) -> Any:
    return obj.get(key)


# ---------------- Tests ----------------


@dataclass
class TestCase:
    id: str
    doc: str
    description: str


@dataclass
class TestOutcome:
    status: str  # PASS/FAIL/SKIP
    errors: List[str]
    context_updates: Dict[str, Any]


def _save_snapshot(out_dir: str, test_id: str, req: Dict[str, Any], resp: HttpResponse) -> None:
    safe_req = json.loads(json.dumps(req))  # deep copy
    if "headers" in safe_req and isinstance(safe_req["headers"], dict):
        if "Authorization" in safe_req["headers"]:
            safe_req["headers"]["Authorization"] = "Bearer <REDACTED>"
    if "query" in safe_req and isinstance(safe_req["query"], dict):
        for k in ["device_token", "access_token", "refresh_token", "client_secret"]:
            if k in safe_req["query"] and safe_req["query"][k] is not None:
                safe_req["query"][k] = "<REDACTED>"
    if "form" in safe_req and isinstance(safe_req["form"], dict):
        for k in ["device_token", "access_token", "refresh_token", "client_secret"]:
            if k in safe_req["form"] and safe_req["form"][k] is not None:
                safe_req["form"][k] = "<REDACTED>"
    safe = {
        "request": safe_req,
        "response": {
            "status": resp.status,
            "headers": resp.headers,
            "raw_text": _redact_tokens(resp.raw_text),
            "json": _redact_json(resp.json),
        },
    }
    _write_json(os.path.join(out_dir, f"{test_id}.snapshot.json"), safe)


def test_user(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/user", token=token)
    _save_snapshot(out_dir, "user_get", {"method": "GET", "path": "/v1/user", "headers": {"Authorization": "Bearer <token>"}}, resp)

    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(_get(resp.json, "status"), "status", errors)
        user = _get(resp.json, "user")
        _expect_obj(user, "user", errors)
        if isinstance(user, dict):
            _expect_str(_get(user, "username"), "user.username", errors)
            sub = user.get("subscription")
            if sub is not None:
                _expect_obj(sub, "user.subscription", errors)
                if isinstance(sub, dict) and "active" in sub:
                    _expect_bool(sub.get("active"), "user.subscription.active", errors)
            prof = user.get("profile")
            if prof is not None:
                _expect_obj(prof, "user.profile", errors)
    else:
        _expect_obj(resp.json, "root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_oauth_device_flow_pending(base_url: str, out_dir: str, client_id: str, client_secret: str) -> TestOutcome:
    """
    Non-interactive auth test:
    - get device_code
    - immediately poll device_token once (expect authorization_pending OR token payload)
    """
    errors: List[str] = []

    r_code = _http_request(
        base_url,
        "POST",
        "/oauth2/device",
        token=None,
        query={"grant_type": "device_code", "client_id": client_id, "client_secret": client_secret},
    )
    _save_snapshot(out_dir, "auth_device_code", {"method": "POST", "path": "/oauth2/device", "query": {"grant_type": "device_code"}}, r_code)
    _require(isinstance(r_code.json, dict), "device_code: expected JSON object", errors)
    code: Optional[str] = None
    if isinstance(r_code.json, dict):
        code = r_code.json.get("code")
        _expect_str(code, "device_code.code", errors)
        _expect_str(r_code.json.get("user_code"), "device_code.user_code", errors)
        _expect_str(r_code.json.get("verification_uri"), "device_code.verification_uri", errors)
        _expect_int(r_code.json.get("expires_in"), "device_code.expires_in", errors)
        _expect_int(r_code.json.get("interval"), "device_code.interval", errors)

    if not code:
        errors.append("device_code: missing code; cannot test device_token polling")
        return TestOutcome(status="FAIL", errors=errors, context_updates={})

    r_poll = _http_request(
        base_url,
        "POST",
        "/oauth2/device",
        token=None,
        query={
            "grant_type": "device_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        },
    )
    _save_snapshot(out_dir, "auth_device_token_poll", {"method": "POST", "path": "/oauth2/device", "query": {"grant_type": "device_token"}}, r_poll)
    _require(isinstance(r_poll.json, dict), "device_token poll: expected JSON object", errors)
    if isinstance(r_poll.json, dict):
        # Either OAuth error (pending) or token payload
        if "error" in r_poll.json:
            _expect_str(r_poll.json.get("error"), "device_token.error", errors)
        else:
            _expect_str(r_poll.json.get("access_token"), "device_token.access_token", errors)
            _expect_str(r_poll.json.get("refresh_token"), "device_token.refresh_token", errors)
            _expect_int(r_poll.json.get("expires_in"), "device_token.expires_in", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_api2_items_search(api2_base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Optional[int]]:
    """
    Reverse-engineering smoke test for KinoPub "api2" endpoints observed in com.kinopub logs.

    Endpoint (from logs / decompiled):
      GET https://<host>/api2/v1.1/items/search?q=...
    """
    errors: List[str] = []
    resp = _http_request(api2_base_url, "GET", "api2/v1.1/items/search", token=token, query={"q": "terminator"})
    _save_snapshot(
        out_dir,
        "api2_items_search",
        {"method": "GET", "base": api2_base_url, "path": "api2/v1.1/items/search", "query": {"q": "terminator"}},
        resp,
    )
    _require(resp.json is not None, "api2 search: response is not JSON", errors)
    item_id: Optional[int] = None
    if isinstance(resp.json, dict):
        # Likely similar to ItemsResponse: {status, items:[{id,...}], ...}
        items = resp.json.get("items")
        if isinstance(items, list) and items:
            it0 = items[0]
            if isinstance(it0, dict) and isinstance(it0.get("id"), int):
                item_id = it0["id"]
        if item_id is None:
            errors.append("api2 search: could not pick itemId from items[]")
    else:
        _expect_obj(resp.json, "api2 search root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), item_id


def test_api2_item_details(api2_base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    """
    Endpoint (from decompiled ExtraInterface2):
      GET api2/v1.1/items/{id}
    """
    errors: List[str] = []
    resp = _http_request(api2_base_url, "GET", f"api2/v1.1/items/{item_id}", token=token)
    _save_snapshot(
        out_dir,
        "api2_item_details",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1.1/items/{item_id}"},
        resp,
    )
    _require(resp.json is not None, "api2 item: response is not JSON", errors)
    meta: Dict[str, Optional[int]] = {"imdb_id": None, "kinopoisk_id": None}
    if isinstance(resp.json, dict):
        # Best-effort sanity: ensure some top-level object fields exist
        if "item" in resp.json:
            _expect_obj(resp.json.get("item"), "api2 item.item", errors)
            if isinstance(resp.json.get("item"), dict):
                it = resp.json["item"]
                imdb = it.get("imdb")
                kp = it.get("kinopoisk")
                if isinstance(imdb, int) and not isinstance(imdb, bool):
                    meta["imdb_id"] = imdb
                if isinstance(kp, int) and not isinstance(kp, bool):
                    meta["kinopoisk_id"] = kp
        elif "id" in resp.json:
            _expect_int(resp.json.get("id"), "api2 item.id", errors)
        else:
            # Not sure yet; keep snapshot for further analysis
            pass
    else:
        _expect_obj(resp.json, "api2 item root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates=meta)


def test_api2_backdrop(api2_base_url: str, token: str, out_dir: str, imdb_id: int, kinopoisk_id: int) -> TestOutcome:
    """
    Endpoint (from decompiled ExtraInterface):
      GET api2/v1/backdrop/{id}?kp_id=...

    Based on naming + other endpoints, `{id}` is likely imdb numeric id.
    """
    errors: List[str] = []
    resp = _http_request(
        api2_base_url,
        "GET",
        f"api2/v1/backdrop/{imdb_id}",
        token=token,
        query={"kp_id": kinopoisk_id},
    )
    _save_snapshot(
        out_dir,
        "api2_backdrop",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1/backdrop/{imdb_id}", "query": {"kp_id": kinopoisk_id}},
        resp,
    )
    if resp.status == 404:
        return TestOutcome(status="SKIP", errors=["api2 backdrop returned 404 (no data for this title or endpoint disabled)"], context_updates={})
    _require(resp.status == 200, f"api2 backdrop: expected HTTP 200 (or 404), got {resp.status}", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_api2_notifications_mutating(api2_base_url: str, token: str, out_dir: str, item_id: int, device_token: str) -> TestOutcome:
    """
    Endpoints (from decompiled ExtraInterface2):
      GET api2/v1.1/notifications/add/{id}?device_token=...
      GET api2/v1.1/notifications/{id}?device_token=...
      GET api2/v1.1/notifications/delete/{id}?device_token=...
    """
    errors: List[str] = []

    r_add = _http_request(api2_base_url, "GET", f"api2/v1.1/notifications/add/{item_id}", token=token, query={"device_token": device_token})
    _save_snapshot(
        out_dir,
        "api2_notifications_add",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1.1/notifications/add/{item_id}", "query": {"device_token": device_token}},
        r_add,
    )
    _require(r_add.status == 200, f"api2 notifications add: expected HTTP 200, got {r_add.status}", errors)
    if r_add.json is not None and not isinstance(r_add.json, dict):
        errors.append(f"api2 notifications add: expected JSON object (or null), got {_type_name(r_add.json)}")

    r_check = _http_request(api2_base_url, "GET", f"api2/v1.1/notifications/{item_id}", token=token, query={"device_token": device_token})
    _save_snapshot(
        out_dir,
        "api2_notifications_check",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1.1/notifications/{item_id}", "query": {"device_token": device_token}},
        r_check,
    )
    _require(r_check.status == 200, f"api2 notifications check: expected HTTP 200, got {r_check.status}", errors)
    if r_check.json is not None and not isinstance(r_check.json, dict):
        errors.append(f"api2 notifications check: expected JSON object (or null), got {_type_name(r_check.json)}")

    r_del = _http_request(api2_base_url, "GET", f"api2/v1.1/notifications/delete/{item_id}", token=token, query={"device_token": device_token})
    _save_snapshot(
        out_dir,
        "api2_notifications_delete",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1.1/notifications/delete/{item_id}", "query": {"device_token": device_token}},
        r_del,
    )
    _require(r_del.status == 200, f"api2 notifications delete: expected HTTP 200, got {r_del.status}", errors)
    if r_del.json is not None and not isinstance(r_del.json, dict):
        errors.append(f"api2 notifications delete: expected JSON object (or null), got {_type_name(r_del.json)}")

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_api2_upload_report(api2_base_url: str, token: str, out_dir: str, filename: str) -> TestOutcome:
    """
    Endpoint (from decompiled ExtraInterface):
      POST api2/v1/upload_report/{filename} (raw body)
    """
    errors: List[str] = []
    body = b"api2 upload_report test\n"
    resp = _http_request(
        api2_base_url,
        "POST",
        f"api2/v1/upload_report/{filename}",
        token=token,
        body=body,
        body_content_type="application/octet-stream",
    )
    _save_snapshot(
        out_dir,
        "api2_upload_report",
        {"method": "POST", "base": api2_base_url, "path": f"api2/v1/upload_report/{filename}", "headers": {"Content-Type": "application/octet-stream"}},
        resp,
    )
    _require(resp.status in (200, 201, 204), f"api2 upload_report: expected HTTP 200/201/204, got {resp.status}", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_api2_item_collections(api2_base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    """
    Endpoint (from decompiled ExtraInterface2):
      GET api2/v1.1/items/collections/{id}
    """
    errors: List[str] = []
    resp = _http_request(api2_base_url, "GET", f"api2/v1.1/items/collections/{item_id}", token=token)
    _save_snapshot(
        out_dir,
        "api2_item_collections",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1.1/items/collections/{item_id}"},
        resp,
    )
    _require(resp.json is not None, "api2 item collections: response is not JSON", errors)
    if isinstance(resp.json, dict):
        # Best-effort: it might be {status, items:[...]} or {items:[...]}.
        if "items" in resp.json:
            _expect_list(resp.json.get("items"), "api2 collections.items", errors)
    else:
        _expect_obj(resp.json, "api2 collections root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_api2_imdb(api2_base_url: str, token: str, out_dir: str, imdb_ids_csv: str) -> TestOutcome:
    """
    Endpoint (from decompiled ExtraInterface + observed logs):
      GET api2/v1/imdb/{id}

    In logs, com.kinopub calls a comma-separated list of ids, but currently receives 404.
    We record the response. If the endpoint returns 404 (as observed), we mark it SKIP.
    """
    errors: List[str] = []
    resp = _http_request(api2_base_url, "GET", f"api2/v1/imdb/{imdb_ids_csv}", token=token)
    _save_snapshot(
        out_dir,
        "api2_imdb",
        {"method": "GET", "base": api2_base_url, "path": f"api2/v1/imdb/{imdb_ids_csv}"},
        resp,
    )
    if resp.status == 404:
        return TestOutcome(status="SKIP", errors=["api2 imdb returned 404 (matches com.kinopub logs)"], context_updates={})
    _require(resp.status == 200, f"api2 imdb: expected HTTP 200 (or 404), got {resp.status}", errors)
    # If it ever becomes available, ensure it is at least JSON-parsable.
    _require(resp.json is not None, "api2 imdb: response is not JSON", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})

def test_types(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, List[int]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/types", token=token)
    _save_snapshot(out_dir, "content_types", {"method": "GET", "path": "/v1/types", "headers": {"Authorization": "Bearer <token>"}}, resp)
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(resp.json.get("status"), "types.status", errors)
        items = resp.json.get("items")
        _expect_list(items, "types.items", errors)
        if isinstance(items, list):
            for i, it in enumerate(items[:5]):
                _expect_obj(it, f"types.items[{i}]", errors)
                if isinstance(it, dict):
                    _expect_str(it.get("id"), f"types.items[{i}].id", errors)
                    _expect_str(it.get("title"), f"types.items[{i}].title", errors)
    else:
        _expect_obj(resp.json, "types.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), []


def test_genres(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/genres", token=token)
    _save_snapshot(out_dir, "content_genres", {"method": "GET", "path": "/v1/genres", "headers": {"Authorization": "Bearer <token>"}}, resp)

    genre_id: Optional[int] = None
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(resp.json.get("status"), "genres.status", errors)
        items = resp.json.get("items")
        _expect_list(items, "genres.items", errors)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and isinstance(it.get("id"), int) and not isinstance(it.get("id"), bool):
                    genre_id = it["id"]
                    break
            for i, it in enumerate(items[:5]):
                _expect_obj(it, f"genres.items[{i}]", errors)
                if isinstance(it, dict):
                    _expect_int(it.get("id"), f"genres.items[{i}].id", errors)
                    _expect_str(it.get("title"), f"genres.items[{i}].title", errors)
    else:
        _expect_obj(resp.json, "genres.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), genre_id


def test_countries(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/countries", token=token)
    _save_snapshot(out_dir, "content_countries", {"method": "GET", "path": "/v1/countries", "headers": {"Authorization": "Bearer <token>"}}, resp)
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(resp.json.get("status"), "countries.status", errors)
        items = resp.json.get("items")
        _expect_list(items, "countries.items", errors)
        if isinstance(items, list):
            for i, it in enumerate(items[:5]):
                _expect_obj(it, f"countries.items[{i}]", errors)
                if isinstance(it, dict):
                    _expect_int(it.get("id"), f"countries.items[{i}].id", errors)
                    _expect_str(it.get("title"), f"countries.items[{i}].title", errors)
    else:
        _expect_obj(resp.json, "countries.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_subtitles(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/subtitles", token=token)
    _save_snapshot(out_dir, "content_subtitles", {"method": "GET", "path": "/v1/subtitles", "headers": {"Authorization": "Bearer <token>"}}, resp)
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        if "status" in resp.json and resp.json["status"] is not None:
            _expect_int(resp.json.get("status"), "subtitles.status", errors)
        items = resp.json.get("items")
        _expect_list(items, "subtitles.items", errors)
        if isinstance(items, list):
            for i, it in enumerate(items[:5]):
                _expect_obj(it, f"subtitles.items[{i}]", errors)
                if isinstance(it, dict):
                    # Different API deployments may return either:
                    # - {id, title}
                    # - {lang, title}
                    if "id" in it and it["id"] is not None:
                        vid = it.get("id")
                        if isinstance(vid, bool) or not isinstance(vid, (int, str)):
                            errors.append(f"subtitles.items[{i}].id: expected int|string, got {_type_name(vid)}")
                    if "lang" in it and it["lang"] is not None:
                        _expect_str(it.get("lang"), f"subtitles.items[{i}].lang", errors)
                    if "title" in it and it["title"] is not None:
                        _expect_str(it.get("title"), f"subtitles.items[{i}].title", errors)
    else:
        _expect_obj(resp.json, "subtitles.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_search(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/search", token=token, query={"q": "terminator", "perpage": 5})
    _save_snapshot(
        out_dir,
        "content_search",
        {"method": "GET", "path": "/v1/items/search", "query": {"q": "terminator", "perpage": 5}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_similar(base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/similar", token=token, query={"id": item_id})
    _save_snapshot(
        out_dir,
        "content_similar",
        {"method": "GET", "path": "/v1/items/similar", "query": {"id": item_id}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_shortcut(base_url: str, token: str, out_dir: str, name: str, *, genre: Optional[str] = None) -> TestOutcome:
    errors: List[str] = []
    query: Dict[str, Any] = {"type": "movie", "page": 1, "perpage": 5}
    if genre is not None:
        query["genre"] = genre

    snap_suffix = "_genre" if genre is not None else ""
    resp = _http_request(base_url, "GET", f"/v1/items/{name}", token=token, query=query)
    _save_snapshot(
        out_dir,
        f"content_{name}{snap_suffix}",
        {"method": "GET", "path": f"/v1/items/{name}", "query": query, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_trailer(base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/trailer", token=token, query={"id": item_id})
    _save_snapshot(
        out_dir,
        "content_trailer",
        {"method": "GET", "path": "/v1/items/trailer", "query": {"id": item_id}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        if "status" in resp.json and resp.json["status"] is not None:
            _expect_int(resp.json.get("status"), "status", errors)
        tr = resp.json.get("trailer")
        if tr is not None:
            # Live API may return either:
            # - trailer: {id, url?, files?}
            # - trailer: [{id, url}, ...]
            if isinstance(tr, dict):
                tid = tr.get("id")
                if tid is not None and not isinstance(tid, (str, int)) or isinstance(tid, bool):
                    errors.append(f"trailer.id: expected string|int, got {_type_name(tid)}")
                if "url" in tr and tr["url"] is not None:
                    _expect_str(tr.get("url"), "trailer.url", errors)
                if "files" in tr and tr["files"] is not None:
                    _expect_list(tr.get("files"), "trailer.files", errors)
            elif isinstance(tr, list):
                if tr:
                    t0 = tr[0]
                    _expect_obj(t0, "trailer[0]", errors)
                    if isinstance(t0, dict):
                        tid = t0.get("id")
                        if tid is not None and (isinstance(tid, bool) or not isinstance(tid, (str, int))):
                            errors.append(f"trailer[0].id: expected string|int, got {_type_name(tid)}")
                        if "url" in t0 and t0["url"] is not None:
                            _expect_str(t0.get("url"), "trailer[0].url", errors)
            else:
                errors.append(f"trailer: expected object or array, got {_type_name(tr)}")
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_comments(base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/comments", token=token, query={"id": item_id})
    _save_snapshot(
        out_dir,
        "content_comments",
        {"method": "GET", "path": "/v1/items/comments", "query": {"id": item_id}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(resp.json.get("status"), "status", errors)
        comments = resp.json.get("comments")
        _expect_list(comments, "comments", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_vote_mutating(base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/vote", token=token, query={"id": item_id, "like": 1})
    _save_snapshot(
        out_dir,
        "content_vote_like",
        {"method": "GET", "path": "/v1/items/vote", "query": {"id": item_id, "like": 1}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_bool(resp.json.get("voted"), "voted", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_collections(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/collections", token=token, query={"page": 1, "perpage": 5})
    _save_snapshot(
        out_dir,
        "collections_list",
        {"method": "GET", "path": "/v1/collections", "query": {"page": 1, "perpage": 5}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    collection_id: Optional[int] = None
    if isinstance(resp.json, dict):
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
        if isinstance(items, list) and items:
            c0 = items[0]
            if isinstance(c0, dict) and isinstance(c0.get("id"), int):
                collection_id = c0["id"]
    else:
        _expect_obj(resp.json, "root", errors)
    if collection_id is None:
        errors.append("could not pick collectionId from /v1/collections")
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), collection_id


def test_collections_sort(base_url: str, token: str, out_dir: str) -> TestOutcome:
    """
    Verify that the optional `sort` parameter is accepted by the API.
    """
    errors: List[str] = []

    # Try a small set of likely valid sort keys; mark PASS if any yields a normal collections payload.
    candidates = ["updated-", "created-", "views-", "watchers-"]
    last_resp: Optional[HttpResponse] = None
    used: Optional[str] = None

    for sort in candidates:
        resp = _http_request(base_url, "GET", "/v1/collections", token=token, query={"sort": sort, "page": 1, "perpage": 5})
        last_resp = resp
        if resp.status != 200 or not isinstance(resp.json, dict):
            continue
        if not isinstance(resp.json.get("items"), list):
            continue
        used = sort
        break

    if used is None:
        errors.append("collections sort: none of the candidate sort values returned a normal {items: []} payload")
        # Save snapshot of the last attempt to help debugging.
        if last_resp is not None:
            _save_snapshot(
                out_dir,
                "collections_list_sort",
                {"method": "GET", "path": "/v1/collections", "query": {"sort": candidates[-1], "page": 1, "perpage": 5}, "headers": {"Authorization": "Bearer <token>"}},
                last_resp,
            )
        return TestOutcome(status="FAIL", errors=errors, context_updates={})

    resp_ok = _http_request(base_url, "GET", "/v1/collections", token=token, query={"sort": used, "page": 1, "perpage": 5})
    _save_snapshot(
        out_dir,
        "collections_list_sort",
        {"method": "GET", "path": "/v1/collections", "query": {"sort": used, "page": 1, "perpage": 5}, "headers": {"Authorization": "Bearer <token>"}},
        resp_ok,
    )

    _require(resp_ok.status == 200, f"collections sort: expected HTTP 200, got {resp_ok.status}", errors)
    _require(resp_ok.json is not None, "collections sort: response is not JSON", errors)
    if isinstance(resp_ok.json, dict):
        if "status" in resp_ok.json and resp_ok.json["status"] is not None:
            _expect_int(resp_ok.json.get("status"), "collections.sort.status", errors)
        _expect_list(resp_ok.json.get("items"), "collections.sort.items", errors)
    else:
        _expect_obj(resp_ok.json, "collections.sort.root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={"sort": used})


def test_collection_items(base_url: str, token: str, out_dir: str, collection_id: int) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/collections/view", token=token, query={"id": collection_id, "page": 1, "perpage": 5})
    _save_snapshot(
        out_dir,
        "collections_view",
        {"method": "GET", "path": "/v1/collections/view", "query": {"id": collection_id, "page": 1, "perpage": 5}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_references(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    for name in ["server-location", "streaming-type", "voiceover-type", "voiceover-author", "video-quality"]:
        resp = _http_request(base_url, "GET", f"/v1/references/{name}", token=token)
        _save_snapshot(out_dir, f"ref_{name}", {"method": "GET", "path": f"/v1/references/{name}"}, resp)
        _require(resp.json is not None, f"{name}: response is not JSON", errors)
        if isinstance(resp.json, dict):
            if "status" in resp.json:
                _expect_int(resp.json.get("status"), f"{name}.status", errors)
            _expect_list(resp.json.get("items"), f"{name}.items", errors)
        else:
            _expect_obj(resp.json, f"{name}.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_tv(base_url: str, token: str, out_dir: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/tv", token=token)
    _save_snapshot(out_dir, "tv_channels", {"method": "GET", "path": "/v1/tv"}, resp)
    _require(resp.json is not None, "tv: response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_int(resp.json.get("status"), "tv.status", errors)
        _expect_list(resp.json.get("channels"), "tv.channels", errors)
    else:
        _expect_obj(resp.json, "tv.root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_watching(base_url: str, token: str, out_dir: str, item_id: int) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/watching", token=token, query={"id": item_id})
    _save_snapshot(out_dir, "watching_info", {"method": "GET", "path": "/v1/watching", "query": {"id": item_id}}, resp)
    _require(resp.json is not None, "watching: response is not JSON", errors)
    if isinstance(resp.json, dict):
        if "status" in resp.json:
            _expect_int(resp.json.get("status"), "watching.status", errors)
    else:
        _expect_obj(resp.json, "watching.root", errors)

    # Lists
    for name in ["movies", "serials"]:
        r = _http_request(base_url, "GET", f"/v1/watching/{name}", token=token)
        _save_snapshot(out_dir, f"watching_{name}", {"method": "GET", "path": f"/v1/watching/{name}"}, r)
        _require(r.json is not None, f"watching/{name}: response is not JSON", errors)
        if isinstance(r.json, dict):
            _expect_list(r.json.get("items"), f"watching/{name}.items", errors)
        else:
            _expect_obj(r.json, f"watching/{name}.root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), None


def test_watching_mutating(base_url: str, token: str, out_dir: str, item_id: int, media_id: int) -> TestOutcome:
    errors: List[str] = []
    # marktime
    r_mt = _http_request(base_url, "GET", "/v1/watching/marktime", token=token, query={"id": item_id, "video": media_id, "time": 120})
    _save_snapshot(out_dir, "watching_marktime", {"method": "GET", "path": "/v1/watching/marktime", "query": {"id": item_id, "video": media_id, "time": 120}}, r_mt)
    _require(isinstance(r_mt.json, dict) and isinstance(r_mt.json.get("status"), int), "marktime: expected {status:int}", errors)

    # toggle watched
    r_t = _http_request(base_url, "GET", "/v1/watching/toggle", token=token, query={"id": item_id, "video": media_id})
    _save_snapshot(out_dir, "watching_toggle", {"method": "GET", "path": "/v1/watching/toggle", "query": {"id": item_id, "video": media_id}}, r_t)
    _require(isinstance(r_t.json, dict) and isinstance(r_t.json.get("status"), int), "toggle: expected {status:int,...}", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_watchlist_toggle_mutating(base_url: str, token: str, out_dir: str, serial_item_id: int) -> TestOutcome:
    errors: List[str] = []
    # Toggle twice to restore
    for i in [1, 2]:
        r = _http_request(base_url, "GET", "/v1/watching/togglewatchlist", token=token, query={"id": serial_item_id})
        _save_snapshot(out_dir, f"watchlist_toggle_{i}", {"method": "GET", "path": "/v1/watching/togglewatchlist", "query": {"id": serial_item_id}}, r)
        _require(isinstance(r.json, dict) and isinstance(r.json.get("status"), int), "togglewatchlist: expected {status:int,...}", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_history(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Dict[str, Optional[int]]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/history", token=token, query={"page": 1, "perpage": 25})
    _save_snapshot(out_dir, "history_list", {"method": "GET", "path": "/v1/history", "query": {"page": 1, "perpage": 25}}, resp)
    _require(resp.json is not None, "history: response is not JSON", errors)

    picked: Dict[str, Optional[int]] = {"media_id": None, "item_id": None}
    if isinstance(resp.json, dict):
        if "history" in resp.json and resp.json["history"] is not None:
            _expect_list(resp.json.get("history"), "history.history", errors)
            if isinstance(resp.json.get("history"), list) and resp.json["history"]:
                h0 = resp.json["history"][0]
                if isinstance(h0, dict):
                    it = h0.get("item")
                    if isinstance(it, dict) and isinstance(it.get("id"), int):
                        picked["item_id"] = it["id"]
                    md = h0.get("media")
                    if isinstance(md, dict) and isinstance(md.get("id"), int):
                        picked["media_id"] = md["id"]
        else:
            # field may be missing; docs say it exists. Record mismatch.
            errors.append("history response missing 'history' field")
    else:
        _expect_obj(resp.json, "history.root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), picked


def test_history_mutating(base_url: str, token: str, out_dir: str, media_id: Optional[int], season_id: Optional[int], item_id: Optional[int]) -> TestOutcome:
    errors: List[str] = []

    if media_id is not None:
        r = _http_request(base_url, "POST", "/v1/history/clear-for-media", token=token, query={"id": media_id})
        _save_snapshot(out_dir, "history_clear_for_media", {"method": "POST", "path": "/v1/history/clear-for-media", "query": {"id": media_id}}, r)
        _require(r.status == 200 and (r.json is None or (isinstance(r.json, dict) and isinstance(r.json.get("status"), int))), "clear-for-media: expected HTTP 200 with JSON null (or {status:int})", errors)
    else:
        errors.append("clear-for-media skipped: no media_id available")

    if season_id is not None:
        r = _http_request(base_url, "POST", "/v1/history/clear-for-season", token=token, query={"id": season_id})
        _save_snapshot(out_dir, "history_clear_for_season", {"method": "POST", "path": "/v1/history/clear-for-season", "query": {"id": season_id}}, r)
        _require(r.status == 200 and (r.json is None or (isinstance(r.json, dict) and isinstance(r.json.get("status"), int))), "clear-for-season: expected HTTP 200 with JSON null (or {status:int})", errors)
    else:
        errors.append("clear-for-season skipped: no season_id available")

    if item_id is not None:
        r = _http_request(base_url, "POST", "/v1/history/clear-for-item", token=token, query={"id": item_id})
        _save_snapshot(out_dir, "history_clear_for_item", {"method": "POST", "path": "/v1/history/clear-for-item", "query": {"id": item_id}}, r)
        _require(r.status == 200 and (r.json is None or (isinstance(r.json, dict) and isinstance(r.json.get("status"), int))), "clear-for-item: expected HTTP 200 with JSON null (or {status:int})", errors)
    else:
        errors.append("clear-for-item skipped: no item_id available")

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_device(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    # List devices
    resp = _http_request(base_url, "GET", "/v1/device", token=token)
    _save_snapshot(out_dir, "device_list", {"method": "GET", "path": "/v1/device"}, resp)
    _require(resp.json is not None, "device: response is not JSON", errors)
    device_id: Optional[int] = None
    if isinstance(resp.json, dict):
        devs = resp.json.get("devices")
        _expect_list(devs, "device.devices", errors)
        if isinstance(devs, list) and devs:
            d0 = devs[0]
            if isinstance(d0, dict) and isinstance(d0.get("id"), int):
                device_id = d0["id"]
            if isinstance(d0, dict) and "is_browser" in d0 and d0["is_browser"] is not None:
                _expect_bool(d0.get("is_browser"), "device.devices[0].is_browser", errors)
    else:
        _expect_obj(resp.json, "device.root", errors)

    # Current device info
    info = _http_request(base_url, "GET", "/v1/device/info", token=token)
    _save_snapshot(out_dir, "device_info", {"method": "GET", "path": "/v1/device/info"}, info)
    _require(info.json is not None, "device/info: response is not JSON", errors)
    if isinstance(info.json, dict):
        dev = info.json.get("device")
        if isinstance(dev, dict) and isinstance(dev.get("id"), int):
            device_id = dev.get("id")
    else:
        _expect_obj(info.json, "device/info.root", errors)

    if device_id is None:
        errors.append("could not pick deviceId from /v1/device or /v1/device/info")
        return TestOutcome(status="FAIL", errors=errors, context_updates={}), None

    # GET device/{id}
    d = _http_request(base_url, "GET", f"/v1/device/{device_id}", token=token)
    _save_snapshot(out_dir, "device_get", {"method": "GET", "path": f"/v1/device/{device_id}"}, d)
    _require(d.json is not None, "device/{id}: response is not JSON", errors)

    # GET device/{id}/settings
    s = _http_request(base_url, "GET", f"/v1/device/{device_id}/settings", token=token)
    _save_snapshot(out_dir, "device_settings_get", {"method": "GET", "path": f"/v1/device/{device_id}/settings"}, s)
    _require(s.json is not None, "device/{id}/settings: response is not JSON", errors)
    if isinstance(s.json, dict):
        _expect_int(s.json.get("status"), "device.settings.status", errors)
        # settings is a map; accept any object/map
        st = s.json.get("settings")
        if st is not None:
            _expect_obj(st, "device.settings.settings", errors)
    else:
        _expect_obj(s.json, "device/settings.root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), device_id


def _extract_setting_value_int(settings_map: Any, key: str) -> Optional[int]:
    if not isinstance(settings_map, dict):
        return None
    entry = settings_map.get(key)
    if not isinstance(entry, dict):
        return None
    val = entry.get("value")
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    # List case: value is list of {id, selected}
    if isinstance(val, list):
        for opt in val:
            if isinstance(opt, dict):
                selected = opt.get("selected")
                if selected in (1, True):
                    if isinstance(opt.get("id"), int):
                        return opt["id"]
        # fallback to first id
        for opt in val:
            if isinstance(opt, dict) and isinstance(opt.get("id"), int):
                return opt["id"]
    return None


def test_device_mutating(base_url: str, token: str, out_dir: str, device_id: int) -> TestOutcome:
    errors: List[str] = []

    # notify (safe mutation)
    r_notify = _http_request(
        base_url,
        "POST",
        "/v1/device/notify",
        token=token,
        form={"title": "KinoPub API Test", "hardware": "PC", "software": "Windows"},
    )
    _save_snapshot(out_dir, "device_notify", {"method": "POST", "path": "/v1/device/notify", "form": {"title": "KinoPub API Test"}}, r_notify)
    _require(isinstance(r_notify.json, dict) and isinstance(r_notify.json.get("status"), int), "device/notify: expected {status:int}", errors)

    # settings update (attempt no-op by re-sending current values)
    s = _http_request(base_url, "GET", f"/v1/device/{device_id}/settings", token=token)
    settings_map = None
    if isinstance(s.json, dict):
        settings_map = s.json.get("settings")

    required_keys = ["supportSsl", "supportHevc", "supportHdr", "support4k", "mixedPlaylist", "streamingType", "serverLocation"]
    form: Dict[str, Any] = {}
    for k in required_keys:
        v = _extract_setting_value_int(settings_map, k)
        if v is None:
            errors.append(f"device settings update skipped: could not extract int value for {k}")
            return TestOutcome(status="FAIL", errors=errors, context_updates={})
        form[k] = v

    r_upd = _http_request(base_url, "POST", f"/v1/device/{device_id}/settings", token=token, form=form)
    _save_snapshot(out_dir, "device_settings_update", {"method": "POST", "path": f"/v1/device/{device_id}/settings", "form": {"...": "redacted"}}, r_upd)
    _require(isinstance(r_upd.json, dict) and isinstance(r_upd.json.get("status"), int), "device settings update: expected {status:int}", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def _pick_first_item_id(items_resp: Any) -> Optional[int]:
    if isinstance(items_resp, dict):
        items = items_resp.get("items")
        if isinstance(items, list) and items:
            it0 = items[0]
            if isinstance(it0, dict) and isinstance(it0.get("id"), int):
                return it0["id"]
    return None


def test_items_listing(base_url: str, token: str, out_dir: str) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    resp = _http_request(
        base_url,
        "GET",
        "/v1/items",
        token=token,
        query={"type": "movie", "page": 1, "perpage": 5, "sort": "updated-"},
    )
    _save_snapshot(
        out_dir,
        "content_items",
        {
            "method": "GET",
            "path": "/v1/items",
            "query": {"type": "movie", "page": 1, "perpage": 5, "sort": "updated-"},
            "headers": {"Authorization": "Bearer <token>"},
        },
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    item_id: Optional[int] = _pick_first_item_id(resp.json)

    if isinstance(resp.json, dict):
        if "status" in resp.json and resp.json["status"] is not None:
            _expect_int(resp.json.get("status"), "status", errors)
        items = resp.json.get("items")
        _expect_list(items, "items", errors)
        if isinstance(items, list) and items:
            it0 = items[0]
            _expect_obj(it0, "items[0]", errors)
            if isinstance(it0, dict):
                _expect_int(it0.get("id"), "items[0].id", errors)
                _expect_str(it0.get("title"), "items[0].title", errors)
                _expect_str(it0.get("type"), "items[0].type", errors)
        pag = resp.json.get("pagination")
        if pag is not None:
            _expect_obj(pag, "pagination", errors)
            if isinstance(pag, dict):
                _expect_int(pag.get("total"), "pagination.total", errors)
                _expect_int(pag.get("current"), "pagination.current", errors)
                _expect_int(pag.get("perpage"), "pagination.perpage", errors)
    else:
        _expect_obj(resp.json, "root", errors)

    if item_id is None:
        errors.append("could not pick itemId from /v1/items response")

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), item_id


def test_items_listing_filters(base_url: str, token: str, out_dir: str) -> TestOutcome:
    """
    Smoke-test optional /v1/items query parameters used by the official app:
      - title
      - conditions[]
      - (plus one extra filter key, representing @QueryMap usage)
    """
    errors: List[str] = []

    # Use conservative, likely-to-work filters.
    # `conditions[]` comes from the decompiled app (ApiInterface.getItems(..., @t("conditions[]") String... conditions)).
    query: Dict[str, Any] = {
        "type": "movie",
        "page": 1,
        "perpage": 5,
        "sort": "updated-",
        "title": "terminator",
        "conditions[]": ["year>=1900"],
        # Extra key example (QueryMap-style): keys vary by client/feature.
        # Use a non-contradictory value here so the response isn't trivially empty.
        "country": "1",
    }

    resp = _http_request(base_url, "GET", "/v1/items", token=token, query=query)
    _save_snapshot(
        out_dir,
        "content_items_filters",
        {"method": "GET", "path": "/v1/items", "query": query, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )

    _require(resp.status == 200, f"items filters: expected HTTP 200, got {resp.status}", errors)
    _require(resp.json is not None, "items filters: response is not JSON", errors)
    if isinstance(resp.json, dict):
        if "status" in resp.json and resp.json["status"] is not None:
            _expect_int(resp.json.get("status"), "items_filters.status", errors)
        _expect_list(resp.json.get("items"), "items_filters.items", errors)
    else:
        _expect_obj(resp.json, "items_filters.root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def _pick_media_id_from_item(item: Any) -> Optional[int]:
    # Try videos[].id first, else seasons[].episodes[].id
    if not isinstance(item, dict):
        return None
    videos = item.get("videos")
    if isinstance(videos, list):
        for v in videos:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                return v["id"]
    seasons = item.get("seasons")
    if isinstance(seasons, list):
        for s in seasons:
            if not isinstance(s, dict):
                continue
            episodes = s.get("episodes")
            if isinstance(episodes, list):
                for e in episodes:
                    if isinstance(e, dict) and isinstance(e.get("id"), int):
                        return e["id"]
    return None


def _pick_season_id_from_item(item: Any) -> Optional[int]:
    if not isinstance(item, dict):
        return None
    seasons = item.get("seasons")
    if isinstance(seasons, list):
        for s in seasons:
            if isinstance(s, dict) and isinstance(s.get("id"), int):
                return s["id"]
    return None


def test_item_details(base_url: str, token: str, out_dir: str, item_id: int) -> Tuple[TestOutcome, Optional[int]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", f"/v1/items/{item_id}", token=token, query={"nolinks": 1})
    _save_snapshot(
        out_dir,
        "content_item_details",
        {"method": "GET", "path": f"/v1/items/{item_id}", "query": {"nolinks": 1}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    media_id: Optional[int] = None
    if isinstance(resp.json, dict):
        item = resp.json.get("item")
        _expect_obj(item, "item", errors)
        if isinstance(item, dict):
            _expect_int(item.get("id"), "item.id", errors)
            _expect_str(item.get("title"), "item.title", errors)
            _expect_str(item.get("type"), "item.type", errors)
            duration = item.get("duration")
            if duration is not None:
                _expect_obj(duration, "item.duration", errors)
                if isinstance(duration, dict) and "average" in duration and duration["average"] is not None:
                    _expect_num(duration.get("average"), "item.duration.average", errors)
            media_id = _pick_media_id_from_item(item)
    else:
        _expect_obj(resp.json, "root", errors)

    if media_id is None:
        errors.append("could not pick mediaId from item details (videos/seasons/episodes)")

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), media_id


def test_media_links(base_url: str, token: str, out_dir: str, media_id: int) -> Tuple[TestOutcome, Optional[Tuple[str, str]]]:
    errors: List[str] = []
    resp = _http_request(base_url, "GET", "/v1/items/media-links", token=token, query={"mid": media_id})
    _save_snapshot(
        out_dir,
        "content_media_links",
        {"method": "GET", "path": "/v1/items/media-links", "query": {"mid": media_id}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    file_and_type: Optional[Tuple[str, str]] = None
    if isinstance(resp.json, dict):
        files = resp.json.get("files")
        _expect_list(files, "files", errors)
        if isinstance(files, list) and files:
            f0 = files[0]
            _expect_obj(f0, "files[0]", errors)
            if isinstance(f0, dict):
                if isinstance(f0.get("file"), str):
                    # Prefer hls4 if present else hls else http
                    urls = f0.get("urls") or f0.get("url")
                    chosen_type = None
                    if isinstance(urls, dict):
                        for t in ("hls4", "hls2", "hls", "http"):
                            if urls.get(t):
                                chosen_type = t
                                break
                    file_and_type = (f0["file"], chosen_type or "http")
                else:
                    errors.append("files[0].file missing or not a string")
    else:
        _expect_obj(resp.json, "root", errors)

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={}), file_and_type


def test_media_video_link(base_url: str, token: str, out_dir: str, file_path: str, stream_type: str) -> TestOutcome:
    errors: List[str] = []
    resp = _http_request(
        base_url,
        "GET",
        "/v1/items/media-video-link",
        token=token,
        query={"file": file_path, "type": stream_type},
    )
    _save_snapshot(
        out_dir,
        "content_media_video_link",
        {"method": "GET", "path": "/v1/items/media-video-link", "query": {"file": "<file>", "type": stream_type}, "headers": {"Authorization": "Bearer <token>"}},
        resp,
    )
    _require(resp.json is not None, "response is not JSON", errors)
    if isinstance(resp.json, dict):
        _expect_str(resp.json.get("url"), "url", errors)
    else:
        _expect_obj(resp.json, "root", errors)
    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def test_bookmarks_mutating(base_url: str, token: str, out_dir: str, item_id: int) -> TestOutcome:
    """
    Create folder -> add item -> remove item -> remove folder.
    """
    errors: List[str] = []
    ts = int(time.time())
    folder_title = f"api-test-{ts}"

    # list folders (read endpoint)
    r_list_before = _http_request(base_url, "GET", "/v1/bookmarks", token=token)
    _save_snapshot(out_dir, "bookmarks_list_before", {"method": "GET", "path": "/v1/bookmarks"}, r_list_before)
    if not isinstance(r_list_before.json, dict) or not isinstance(r_list_before.json.get("items"), list):
        errors.append("bookmarks list: unexpected response (expected object with items[])")

    # create folder
    r_create = _http_request(base_url, "POST", "/v1/bookmarks/create", token=token, form={"title": folder_title})
    _save_snapshot(out_dir, "bookmarks_create_folder", {"method": "POST", "path": "/v1/bookmarks/create", "form": {"title": folder_title}}, r_create)
    folder_id: Optional[int] = None
    if isinstance(r_create.json, dict):
        folder = r_create.json.get("folder")
        if isinstance(folder, dict) and isinstance(folder.get("id"), int):
            folder_id = folder["id"]
    if folder_id is None:
        errors.append("failed to create bookmark folder (no folder.id)")
        return TestOutcome(status="FAIL", errors=errors, context_updates={})

    # list folders again, ensure our folder exists
    r_list_after = _http_request(base_url, "GET", "/v1/bookmarks", token=token)
    _save_snapshot(out_dir, "bookmarks_list_after", {"method": "GET", "path": "/v1/bookmarks"}, r_list_after)
    if isinstance(r_list_after.json, dict) and isinstance(r_list_after.json.get("items"), list):
        found = False
        for f in r_list_after.json["items"]:
            if isinstance(f, dict) and f.get("id") == folder_id:
                found = True
                break
        if not found:
            errors.append("bookmarks list: created folder not found in items[]")
    else:
        errors.append("bookmarks list: unexpected response after create")

    # add item
    r_add = _http_request(base_url, "POST", "/v1/bookmarks/add", token=token, form={"item": item_id, "folder": folder_id})
    _save_snapshot(out_dir, "bookmarks_add_item", {"method": "POST", "path": "/v1/bookmarks/add", "form": {"item": item_id, "folder": folder_id}}, r_add)
    if not isinstance(r_add.json, dict) or (r_add.json.get("status") is None):
        errors.append("bookmark add: unexpected response (expected object with status)")

    # folder items (read endpoint)
    r_folder_items = _http_request(base_url, "GET", f"/v1/bookmarks/{folder_id}", token=token, query={"page": 1})
    _save_snapshot(out_dir, "bookmarks_folder_items", {"method": "GET", "path": f"/v1/bookmarks/{folder_id}", "query": {"page": 1}}, r_folder_items)
    if not isinstance(r_folder_items.json, dict) or not isinstance(r_folder_items.json.get("items"), list):
        errors.append("bookmarks folder items: unexpected response (expected object with items[])")

    # item folders (read endpoint)
    r_item_folders = _http_request(base_url, "GET", "/v1/bookmarks/get-item-folders", token=token, query={"item": item_id})
    _save_snapshot(out_dir, "bookmarks_item_folders", {"method": "GET", "path": "/v1/bookmarks/get-item-folders", "query": {"item": item_id}}, r_item_folders)
    if not isinstance(r_item_folders.json, dict) or not isinstance(r_item_folders.json.get("folders"), list):
        errors.append("bookmarks get-item-folders: unexpected response (expected object with folders[])")

    # remove item
    r_rm_item = _http_request(base_url, "POST", "/v1/bookmarks/remove-item", token=token, form={"item": item_id, "folder": folder_id})
    _save_snapshot(out_dir, "bookmarks_remove_item", {"method": "POST", "path": "/v1/bookmarks/remove-item", "form": {"item": item_id, "folder": folder_id}}, r_rm_item)
    if not isinstance(r_rm_item.json, dict) or (r_rm_item.json.get("status") is None):
        errors.append("bookmark remove-item: unexpected response (expected object with status)")

    # remove folder (cleanup)
    r_rm_folder = _http_request(base_url, "POST", "/v1/bookmarks/remove-folder", token=token, form={"folder": folder_id})
    _save_snapshot(out_dir, "bookmarks_remove_folder", {"method": "POST", "path": "/v1/bookmarks/remove-folder", "form": {"folder": folder_id}}, r_rm_folder)
    if not isinstance(r_rm_folder.json, dict) or (r_rm_folder.json.get("status") is None):
        errors.append("bookmark remove-folder: unexpected response (expected object with status)")

    return TestOutcome(status="PASS" if not errors else "FAIL", errors=errors, context_updates={})


def _run_all(
    base_url: str,
    token_arg: Optional[str],
    token_file: str,
    client_id: Optional[str],
    client_secret: Optional[str],
    include_mutating: bool,
    include_destructive: bool,
    include_api2: bool,
    api2_base_url: Optional[str],
    api2_device_token: Optional[str],
    api2_upload_report: bool,
) -> int:
    root_out = os.path.join(_script_dir(), "output", _now_stamp())
    _safe_mkdir(root_out)

    print(f"Output dir: {root_out}")
    print("Note: snapshots may include personal account data returned by the API. Do NOT commit/share them.")
    if include_mutating:
        print("WARNING: mutating tests enabled (bookmarks/votes/watchlist/device/etc). Use a test account.")
    if include_destructive:
        print("DANGER: destructive tests enabled (history clears). Use a test account.")

    token, token_source = _resolve_access_token(token_arg, token_file)
    _write_json(
        os.path.join(root_out, "token_source.json"),
        {
            "source": token_source,
            "token_file": token_file,
            "token_meta": {"len": (len(token) if isinstance(token, str) else None)},
        },
    )
    if not token:
        print(
            "FAIL: Could not obtain access token. Provide --token, set KINOPUB_ACCESS_TOKEN, "
            f"or put it into: {token_file} (or run extract_token.py to generate it)."
        )
        return 2

    results: List[Tuple[str, str, List[str]]] = []

    def add(test_id: str, outcome: TestOutcome) -> None:
        results.append((test_id, outcome.status, outcome.errors))

    # --- Auth + basic ---
    if client_id and client_secret:
        add("test-auth-oauth2-device-flow", test_oauth_device_flow_pending(base_url, root_out, client_id, client_secret))
    else:
        add("test-auth-oauth2-device-flow", TestOutcome(status="SKIP", errors=["client_id/client_secret not available"], context_updates={}))

    add("test-user", test_user(base_url, token, root_out))

    # References + TV
    add("test-references", test_references(base_url, token, root_out))
    add("test-tv", test_tv(base_url, token, root_out))

    # Content catalog (arrays)
    add("test-content-types", test_types(base_url, token, root_out)[0])
    o_genres, genre_id = test_genres(base_url, token, root_out)
    add("test-content-genres", o_genres)
    add("test-content-countries", test_countries(base_url, token, root_out))
    add("test-content-subtitles", test_subtitles(base_url, token, root_out))

    # Content listing + details
    o_items, item_id = test_items_listing(base_url, token, root_out)
    add("test-content-items", o_items)
    add("test-content-items-filters", test_items_listing_filters(base_url, token, root_out))

    if item_id is None:
        # Can't proceed to media-dependent tests.
        _write_json(os.path.join(root_out, "summary.json"), {"results": results})
        _print_summary(results, root_out)
        return 1

    o_det, media_id = test_item_details(base_url, token, root_out, item_id)
    add("test-content-item-details", o_det)

    # Content search/similar/shortcuts
    add("test-content-search", test_search(base_url, token, root_out))
    add("test-content-similar", test_similar(base_url, token, root_out, item_id))
    for sc in ["fresh", "hot", "popular"]:
        add(f"test-content-{sc}", test_shortcut(base_url, token, root_out, sc))
        if genre_id is not None:
            add(f"test-content-{sc}-genre", test_shortcut(base_url, token, root_out, sc, genre=str(genre_id)))
        else:
            add(f"test-content-{sc}-genre", TestOutcome(status="SKIP", errors=["could not pick genre_id from /v1/genres"], context_updates={}))

    # Trailer/comments/vote (mutating vote)
    add("test-content-trailer", test_trailer(base_url, token, root_out, item_id))
    add("test-content-comments", test_comments(base_url, token, root_out, item_id))
    if include_mutating:
        add("test-content-vote-mutating", test_vote_mutating(base_url, token, root_out, item_id))
    else:
        add(
            "test-content-vote-mutating",
            TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
        )

    if media_id is not None:
        o_links, file_and_type = test_media_links(base_url, token, root_out, media_id)
        add("test-content-media-links", o_links)
        if file_and_type:
            fpath, stype = file_and_type
            o_link = test_media_video_link(base_url, token, root_out, fpath, stype)
            add("test-content-media-video-link", o_link)

    # Collections
    o_cols, col_id = test_collections(base_url, token, root_out)
    add("test-collections", o_cols)
    add("test-collections-sort", test_collections_sort(base_url, token, root_out))
    if col_id is not None:
        add("test-collections-view", test_collection_items(base_url, token, root_out, col_id))

    # Bookmarks: mutating create/add/remove cleanup
    if include_mutating:
        add("test-bookmarks-mutating", test_bookmarks_mutating(base_url, token, root_out, item_id))
    else:
        add(
            "test-bookmarks-mutating",
            TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
        )

    # Watching (read + mutating)
    add("test-watching", test_watching(base_url, token, root_out, item_id)[0])
    if include_mutating:
        if media_id is not None:
            add("test-watching-mutating", test_watching_mutating(base_url, token, root_out, item_id, media_id))
        else:
            add(
                "test-watching-mutating",
                TestOutcome(status="SKIP", errors=["no media_id available for watching mutation tests"], context_updates={}),
            )
    else:
        add(
            "test-watching-mutating",
            TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
        )

    # Pick a serial item for watchlist toggles / season id (for destructive history tests).
    season_id: Optional[int] = None
    serial_item_id: Optional[int] = None
    if include_mutating or include_destructive:
        serial_resp = _http_request(
            base_url,
            "GET",
            "/v1/items",
            token=token,
            query={"type": "serial", "page": 1, "perpage": 5, "sort": "updated-"},
        )
        _save_snapshot(
            root_out,
            "content_items_serial",
            {"method": "GET", "path": "/v1/items", "query": {"type": "serial", "page": 1, "perpage": 5}},
            serial_resp,
        )
        serial_item_id = _pick_first_item_id(serial_resp.json)

    if include_mutating:
        if serial_item_id is not None:
            add("test-watchlist-toggle-mutating", test_watchlist_toggle_mutating(base_url, token, root_out, serial_item_id))
        else:
            add(
                "test-watchlist-toggle-mutating",
                TestOutcome(status="SKIP", errors=["could not pick serial item id from /v1/items?type=serial"], context_updates={}),
            )
    else:
        add(
            "test-watchlist-toggle-mutating",
            TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
        )

    if include_destructive and serial_item_id is not None:
        serial_det = _http_request(base_url, "GET", f"/v1/items/{serial_item_id}", token=token, query={"nolinks": 1})
        _save_snapshot(root_out, "serial_item_details", {"method": "GET", "path": f"/v1/items/{serial_item_id}", "query": {"nolinks": 1}}, serial_det)
        if isinstance(serial_det.json, dict):
            season_id = _pick_season_id_from_item(serial_det.json.get("item"))

    # History (read + destructive clears)
    o_hist, picked = test_history(base_url, token, root_out)
    add("test-history", o_hist)
    if include_destructive:
        add(
            "test-history-mutating",
            test_history_mutating(base_url, token, root_out, picked.get("media_id"), season_id, picked.get("item_id") or item_id),
        )
    else:
        add(
            "test-history-mutating",
            TestOutcome(status="SKIP", errors=["destructive tests disabled (enable with --include-destructive)"], context_updates={}),
        )

    # Device (read + safe mutations)
    o_dev, dev_id = test_device(base_url, token, root_out)
    add("test-device", o_dev)
    if include_mutating:
        if dev_id is not None:
            add("test-device-mutating", test_device_mutating(base_url, token, root_out, dev_id))
        else:
            add("test-device-mutating", TestOutcome(status="SKIP", errors=["no device_id available"], context_updates={}))
    else:
        add(
            "test-device-mutating",
            TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
        )

    # -------- api2 (\"v2\") reverse-engineering smoke tests --------
    if include_api2:
        api2_base = api2_base_url or _derive_api2_base_url(base_url)
        api2_search_outcome, api2_item_id = test_api2_items_search(api2_base, token, root_out)
        add("test-api2-items-search", api2_search_outcome)
        chosen_item_id = api2_item_id or item_id
        api2_item_outcome = test_api2_item_details(api2_base, token, root_out, chosen_item_id)
        add("test-api2-item-details", api2_item_outcome)
        add("test-api2-item-collections", test_api2_item_collections(api2_base, token, root_out, chosen_item_id))
        imdb_id = None
        kp_id = None
        if isinstance(api2_item_outcome.context_updates, dict):
            imdb_id = api2_item_outcome.context_updates.get("imdb_id")
            kp_id = api2_item_outcome.context_updates.get("kinopoisk_id")
        if isinstance(imdb_id, int) and isinstance(kp_id, int):
            add("test-api2-backdrop", test_api2_backdrop(api2_base, token, root_out, imdb_id, kp_id))
            # Try imdb endpoint with a real id (still often 404 per observed logs)
            add("test-api2-imdb", test_api2_imdb(api2_base, token, root_out, str(imdb_id)))
        else:
            add("test-api2-backdrop", TestOutcome(status="SKIP", errors=["api2 backdrop skipped: could not extract imdb_id/kinopoisk_id"], context_updates={}))
            add("test-api2-imdb", TestOutcome(status="SKIP", errors=["api2 imdb skipped: could not extract imdb_id"], context_updates={}))

        if api2_device_token:
            if include_mutating:
                add(
                    "test-api2-notifications-mutating",
                    test_api2_notifications_mutating(api2_base, token, root_out, chosen_item_id, api2_device_token),
                )
            else:
                add(
                    "test-api2-notifications-mutating",
                    TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}),
                )
        else:
            add("test-api2-notifications-mutating", TestOutcome(status="SKIP", errors=["api2 notifications skipped: provide --api2-device-token"], context_updates={}))

        if api2_upload_report and include_mutating:
            add("test-api2-upload-report", test_api2_upload_report(api2_base, token, root_out, filename="kinopub_test.txt"))
        elif api2_upload_report and not include_mutating:
            add("test-api2-upload-report", TestOutcome(status="SKIP", errors=["mutating tests disabled (enable with --include-mutating)"], context_updates={}))
        else:
            add("test-api2-upload-report", TestOutcome(status="SKIP", errors=["api2 upload_report skipped (enable with --api2-upload-report)"], context_updates={}))
    else:
        add("test-api2", TestOutcome(status="SKIP", errors=["api2 tests not enabled (use --include-api2)"], context_updates={}))

    _write_json(os.path.join(root_out, "summary.json"), {"results": results})
    _print_summary(results, root_out)
    # Treat SKIP as non-failing; only FAIL should produce a failing exit code.
    return 0 if all(s != "FAIL" for _, s, _ in results) else 1


def _print_summary(results: List[Tuple[str, str, List[str]]], out_dir: str) -> None:
    print("")
    print("KinoPub API test summary")
    print(f"- Output: {out_dir}")
    print("")
    for test_id, status, errs in results:
        print(f"{status:4} {test_id}")
        for e in errs[:10]:
            print(f"  - {e}")
        if len(errs) > 10:
            print(f"  - ... {len(errs) - 10} more")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_URL_DEFAULT)
    ap.add_argument("--token", default=None, help="Access token for Authorization: Bearer <token> (overrides env/file)")
    ap.add_argument("--token-file", default=_default_token_file(), help="Read token from file if --token and env are not provided")
    ap.add_argument("--client-id", default=os.environ.get("KINOPUB_CLIENT_ID"), help="OAuth client_id (optional; used only for OAuth test)")
    ap.add_argument("--client-secret", default=os.environ.get("KINOPUB_CLIENT_SECRET"), help="OAuth client_secret (optional; used only for OAuth test)")
    ap.add_argument("--include-mutating", action="store_true", help="Enable tests that modify account state (votes/bookmarks/watchlist/device/etc)")
    ap.add_argument("--include-destructive", action="store_true", help="Enable destructive tests (history clear endpoints)")
    ap.add_argument("--include-api2", action="store_true", help="Run reverse-engineering smoke tests for api2/* endpoints")
    ap.add_argument("--api2-base-url", default=None, help="Base URL for api2 endpoints (default: derived from --base-url)")
    ap.add_argument("--api2-device-token", default=os.environ.get("KINOPUB_API2_DEVICE_TOKEN"), help="Device token for api2 notifications endpoints (optional)")
    ap.add_argument("--api2-upload-report", action="store_true", help="Enable api2 upload_report POST test (mutating; requires --include-mutating)")
    args = ap.parse_args()

    return _run_all(
        base_url=args.base_url,
        token_arg=args.token,
        token_file=args.token_file,
        client_id=args.client_id,
        client_secret=args.client_secret,
        include_mutating=args.include_mutating,
        include_destructive=args.include_destructive,
        include_api2=args.include_api2,
        api2_base_url=args.api2_base_url,
        api2_device_token=args.api2_device_token,
        api2_upload_report=args.api2_upload_report,
    )


if __name__ == "__main__":
    raise SystemExit(main())

