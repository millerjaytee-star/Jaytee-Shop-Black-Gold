"""Deploy smoke for Ask Stabilis, browser assets, authorization edge, and AI Gateway."""
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
        with urlopen(req, timeout=45) as response:
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
        with urlopen(req, timeout=45) as response:
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

    status, body = get("/api/stabilis-ai-health?token=stabilis-health-a81f9d4c-20260901")
    assert status == 200, (status, body)
    payload = json.loads(body)
    assert payload.get("ok") is True, payload
    assert payload.get("provider") == "netlify-ai-gateway/openai", payload
    # The gateway may return the provider's pinned model snapshot ID (for
    # example gpt-5-2025-08-07) even when Stabilis requests the gpt-5 alias.
    # Verify the intended model family without rejecting a legitimate pin.
    model = str(payload.get("model") or "")
    assert model == "gpt-5" or model.startswith("gpt-5-"), payload
    print("ASK STABILIS AI GATEWAY PROVIDER SMOKE = PASS")


if __name__ == "__main__":
    main()
