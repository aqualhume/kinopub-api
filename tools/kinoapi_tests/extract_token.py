import argparse
import datetime as _dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


"""
KinoPub OAuth2 Device Flow helper.

This script is intended as:
- a runnable example of the authentication flow described in `api/v1/authentication.md`
- a convenience tool that stores the access token where `run_tests.py` expects it:
    tools/kinoapi_tests/.local/access_token.txt

Security notes:
- The generated token file is under `.local/` (ignored by `.gitignore`). Do NOT commit/share it.
"""


BASE_URL_DEFAULT = "https://api.service-kp.com/"
ENV_CLIENT_ID = "KINOPUB_CLIENT_ID"
ENV_CLIENT_SECRET = "KINOPUB_CLIENT_SECRET"


def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _default_token_file() -> str:
    return os.path.join(_script_dir(), ".local", "access_token.txt")


def _ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else (url + "/")


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    raw_text: str
    json: Optional[Any]


def _is_json_content_type(headers: Dict[str, str]) -> bool:
    ct = headers.get("Content-Type", "")
    return "application/json" in ct or "application/js" in ct or "+json" in ct


def _http_post_query(base_url: str, path: str, query: Dict[str, Any], timeout_s: int = 30) -> HttpResponse:
    base_url = _ensure_trailing_slash(base_url)
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)

    req = urllib.request.Request(url, method="POST", headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, data=b"", timeout=timeout_s) as resp:
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


def _safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))
        f.write("\n")


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat()


def _mask(s: str, keep: int = 6) -> str:
    s = s or ""
    if len(s) <= keep:
        return "<redacted>"
    return s[:keep] + "…" + f"(len={len(s)})"


def _print_remaining(deadline: float) -> None:
    remaining_s = max(0, int(deadline - time.time()))
    mm, ss = divmod(remaining_s, 60)
    # Single-line status that overwrites itself.
    # Minutes are fixed-width to avoid leftover characters when going from 100+ -> 2 digits.
    sys.stdout.write(f"\rWaiting for authorization... remaining {mm:4d}:{ss:02d}")
    sys.stdout.flush()


def _device_flow(
    base_url: str,
    client_id: str,
    client_secret: str,
    *,
    open_browser: bool,
    timeout_s: int,
) -> Dict[str, Any]:
    # Step 1: request device_code
    r_code = _http_post_query(
        base_url,
        "/oauth2/device",
        query={"grant_type": "device_code", "client_id": client_id, "client_secret": client_secret},
        timeout_s=timeout_s,
    )
    if not isinstance(r_code.json, dict):
        raise RuntimeError(f"device_code: expected JSON object, got HTTP {r_code.status}: {r_code.raw_text[:200]}")

    code = r_code.json.get("code")
    user_code = r_code.json.get("user_code")
    verification_uri = r_code.json.get("verification_uri") or r_code.json.get("verification_uri_complete")
    expires_in = r_code.json.get("expires_in")
    interval = r_code.json.get("interval")

    if not isinstance(code, str) or not code:
        raise RuntimeError("device_code: missing 'code'")
    if not isinstance(user_code, str) or not user_code:
        raise RuntimeError("device_code: missing 'user_code'")
    if not isinstance(verification_uri, str) or not verification_uri:
        raise RuntimeError("device_code: missing 'verification_uri'")
    if not isinstance(expires_in, int):
        raise RuntimeError("device_code: missing/invalid 'expires_in'")
    if not isinstance(interval, int):
        raise RuntimeError("device_code: missing/invalid 'interval'")

    print("")
    print("OAuth2 Device Flow")
    print("")
    print("1) Open this URL in a browser:")
    print(f"   {verification_uri}")
    print("2) Enter this code:")
    print(f"   {user_code}")
    print("")
    print(f"Device code expires in ~{expires_in}s. Poll interval: {interval}s.")
    print("")

    if open_browser:
        try:
            webbrowser.open(verification_uri)
        except Exception:
            pass

    # Step 2: poll for access token
    deadline = time.time() + max(1, expires_in)
    poll_interval = max(1, interval)
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        r_poll = _http_post_query(
            base_url,
            "/oauth2/device",
            query={"grant_type": "device_token", "client_id": client_id, "client_secret": client_secret, "code": code},
            timeout_s=timeout_s,
        )

        if isinstance(r_poll.json, dict) and isinstance(r_poll.json.get("access_token"), str):
            # Finish the status line cleanly.
            sys.stdout.write("\r" + (" " * 80) + "\r")
            sys.stdout.flush()
            return r_poll.json

        if isinstance(r_poll.json, dict) and isinstance(r_poll.json.get("error"), str):
            err = r_poll.json.get("error")
            if err == "authorization_pending":
                # User hasn't finished authorizing yet.
                _print_remaining(deadline)
            elif err == "slow_down":
                poll_interval += 5
                _print_remaining(deadline)
            elif err in ("expired_token", "access_denied"):
                sys.stdout.write("\n")
                raise RuntimeError(f"device_token: {err}")
            else:
                sys.stdout.write("\n")
                raise RuntimeError(f"device_token: unexpected OAuth error: {r_poll.json}")
        else:
            # Non-OAuth unexpected response (HTML, plain text, etc.)
            sys.stdout.write("\n")
            raise RuntimeError(f"device_token: unexpected response HTTP {r_poll.status}: {r_poll.raw_text[:200]}")

        # Respect server-provided interval (and any slow_down backoff).
        time.sleep(poll_interval)

    sys.stdout.write("\n")
    raise RuntimeError("device_token: timed out waiting for user authorization (device code expired)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_URL_DEFAULT, help="API base URL (must expose /oauth2/device)")
    ap.add_argument("--client-id", default=os.environ.get(ENV_CLIENT_ID), help=f"OAuth client_id (or env {ENV_CLIENT_ID})")
    ap.add_argument(
        "--client-secret",
        default=os.environ.get(ENV_CLIENT_SECRET),
        help=f"OAuth client_secret (or env {ENV_CLIENT_SECRET})",
    )
    ap.add_argument(
        "--token-file",
        default=_default_token_file(),
        help="Where to write the token JSON (default: same path used by run_tests.py)",
    )
    ap.add_argument("--open-browser", action="store_true", help="Try to open the verification URL in a browser")
    ap.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    args = ap.parse_args()

    if not args.client_id or not args.client_secret:
        print("Missing credentials.")
        print(f"Provide --client-id/--client-secret or set env {ENV_CLIENT_ID}/{ENV_CLIENT_SECRET}.")
        return 2

    base_url = _ensure_trailing_slash(args.base_url)

    token_payload = _device_flow(
        base_url,
        client_id=str(args.client_id),
        client_secret=str(args.client_secret),
        open_browser=bool(args.open_browser),
        timeout_s=int(args.timeout),
    )

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")

    out_obj: Dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_payload.get("token_type"),
        "expires_in": token_payload.get("expires_in"),
        "scope": token_payload.get("scope"),
        "obtained_at": _now_iso(),
        "base_url": base_url,
        "note": "Generated by tools/kinoapi_tests/extract_token.py. Do NOT commit/share this file.",
    }

    token_dir = os.path.dirname(os.path.abspath(args.token_file))
    _safe_mkdir(token_dir)
    _write_json(args.token_file, out_obj)

    print("Token obtained.")
    print(f"- access_token: {_mask(str(access_token))}")
    if isinstance(refresh_token, str) and refresh_token:
        print(f"- refresh_token: {_mask(refresh_token)}")
    print(f"- written to: {os.path.abspath(args.token_file)}")
    print("")
    print("Next:")
    print(f'  python3 "{os.path.join(_script_dir(), "run_tests.py")}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

