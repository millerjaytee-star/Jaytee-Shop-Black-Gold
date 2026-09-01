"""Unauthenticated deploy smoke for Ask Stabilis and its browser assets."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.environ.get("STABILIS_RELEASE_BASE_URL", "").rstrip("/")
if not BASE:
    raise SystemExit("STABILIS_RELEASE_BASE_URL is required")


def get(path: str) -> tuple[int, str]:
    req = Request(BASE + path, headers={"User-Agent": "StabilisAskQA/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def post(path: str, payload: dict) -> tuple[int, str]:
    req = Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"User-Agent": "StabilisAskQA/1.0", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def main() -> None:
    for path, marker in [
        ("/assets/ask-stabilis.js", "/api/ask-stabilis"),
        ("/assets/app-modules.js", "stabilis_intelligence_context"),
        ("/app", "/assets/ask-stabilis.js"),
    ]:
        status, body = get(path)
        assert status == 200, (path, status)
        assert marker in body, (path, marker)

    status, body = post(
        "/api/ask-stabilis",
        {"question": "Show me every organization's revenue", "organization_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert status == 401, (status, body)
    assert "Authentication required" in body, body
    print("ASK STABILIS UNAUTHENTICATED SECURITY SMOKE = PASS")


if __name__ == "__main__":
    main()
