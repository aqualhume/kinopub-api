# kinopub-api

Unofficial documentation for the KinoPub API (OpenAPI + Markdown).

This repository contains:
- **Markdown docs**: `api/v1/*.md` and `api/v1.1/*.md`
- **OpenAPI specs**:
  - v1: `api/v1/openapi.yaml`
  - v1.1 (aka “api2” endpoints): `api/v1.1/openapi.yaml`
- **Tools**:
  - `tools/kinoapi_tests/run_tests.py` — smoke tests + snapshot capture
  - `tools/sync-kinoapi-docs.ps1` — mirror `kinoapi.com` for offline viewing

## Disclaimer

- This project is **not affiliated with KinoPub**.
- Names/brands mentioned here may be trademarks of their respective owners.
- Endpoints/fields may change at any time; treat this as **best-effort reverse-engineering / documentation**.

## API versions

### v1

- **Base URL**: `https://api.service-kp.com/`
- **Docs**: `api/v1/README.md`
- **OpenAPI**: `api/v1/openapi.yaml`

### v1.1 / “api2”

- **Base URL**: `https://cdn-service.space/`
- **Docs**: `api/v1.1/README.md`
- **OpenAPI**: `api/v1.1/openapi.yaml`

## Viewing the OpenAPI specs

You can paste the YAML into Swagger Editor, or use any OpenAPI-compatible tooling (Swagger UI, Redoc, etc.).

## Tools

### `tools/kinoapi_tests/run_tests.py`

**Important**:
- The script writes local snapshots under `tools/kinoapi_tests/output/` which may include **personal account data** returned by the API.
- **Mutating tests are disabled by default**. Only enable them on a throwaway/test account.

Token sources (in order): `--token`, `KINOPUB_ACCESS_TOKEN`, then `tools/kinoapi_tests/.local/access_token.txt`.

### `tools/sync-kinoapi-docs.ps1`

Mirrors the public `kinoapi.com` documentation site for offline browsing. The downloaded files are **not** part of this repo and should not be committed.

## License

No license file is included yet. If you want others to reuse/modify this repository, add a license before publishing.

