"""Browser-level release QA for the Stabilis Netlify deploy preview.

Runs against the real deploy-preview URL. It checks route rendering, browser console/page
errors, failed same-origin assets, security headers, desktop/tablet/mobile overflow, and
critical Operator Intelligence demo deep links. No customer credentials are used.
"""
from __future__ import annotations

import os
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from playwright.sync_api import Browser, Page, sync_playwright

BASE = os.environ.get("STABILIS_RELEASE_BASE_URL", "").rstrip("/")
if not BASE:
    raise SystemExit("STABILIS_RELEASE_BASE_URL is required")

ROUTES = [
    "/",
    "/operator-intelligence",
    "/operator-intelligence-report",
    "/login",
    "/app",
    "/security",
    "/privacy",
    "/terms",
]
DEMO_HASHES = [
    "command",
    "morning",
    "locations",
    "labor",
    "forecast",
    "inventory",
    "purchasing",
    "food",
    "revenue",
    "opportunities",
    "actions",
    "results",
    "reports",
    "intelligence",
    "alerts",
    "data",
    "expansion",
    "scenarios",
    "weekly",
    "period-close",
]
VIEWPORTS = [
    ("desktop", {"width": 1440, "height": 1000}),
    ("tablet", {"width": 820, "height": 1180}),
    ("mobile", {"width": 390, "height": 844}),
]


def wait_for_preview() -> None:
    deadline = time.time() + 180
    last = ""
    while time.time() < deadline:
        try:
            req = Request(BASE + "/", headers={"User-Agent": "StabilisReleaseQA/1.0"})
            with urlopen(req, timeout=15) as response:
                if 200 <= response.status < 400:
                    print(f"Preview ready: HTTP {response.status}")
                    return
                last = f"HTTP {response.status}"
        except (URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(5)
    raise AssertionError(f"Deploy preview did not become reachable: {last}")


def check_headers() -> None:
    for path in ["/", "/app", "/login"]:
        req = Request(BASE + path, headers={"User-Agent": "StabilisReleaseQA/1.0"})
        with urlopen(req, timeout=20) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            assert response.status == 200, (path, response.status)
            for name in [
                "content-security-policy",
                "strict-transport-security",
                "x-content-type-options",
                "referrer-policy",
                "permissions-policy",
                "x-frame-options",
            ]:
                assert headers.get(name), f"{path}: missing {name}"
            if path in {"/app", "/login"}:
                assert "no-store" in headers.get("cache-control", "").lower(), (
                    path,
                    headers.get("cache-control"),
                )
            if path == "/app":
                assert "noindex" in headers.get("x-robots-tag", "").lower(), headers.get("x-robots-tag")
    print("Security headers: PASS")


def attach_error_capture(page: Page, errors: list[str]) -> None:
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on(
        "console",
        lambda msg: errors.append(f"console:{msg.type}: {msg.text}") if msg.type == "error" else None,
    )
    page.on(
        "requestfailed",
        lambda req: errors.append(f"requestfailed: {req.method} {req.url} {req.failure}"),
    )
    page.on(
        "response",
        lambda resp: errors.append(f"asset-http-{resp.status}: {resp.url}")
        if resp.status >= 400 and resp.url.startswith(BASE) and resp.request.resource_type in {"script", "stylesheet", "image", "font"}
        else None,
    )


def visit(browser: Browser, label: str, viewport: dict[str, int]) -> None:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    errors: list[str] = []
    attach_error_capture(page, errors)
    for path in ROUTES:
        response = page.goto(BASE + path, wait_until="networkidle", timeout=45_000)
        assert response is not None, path
        assert response.status < 400, (path, response.status)
        page.wait_for_timeout(250)
        if path == "/app":
            assert page.url.startswith(BASE + "/login") or page.url.startswith(BASE + "/app"), page.url
        width = page.evaluate("Math.max(document.body.scrollWidth,document.documentElement.scrollWidth)")
        client = page.evaluate("document.documentElement.clientWidth")
        assert width <= client + 4, f"{label} horizontal overflow on {path}: {width}>{client}"
        body = page.locator("body").inner_text(timeout=10_000)
        assert body.strip(), f"blank body on {path}"
    context.close()
    assert not errors, f"{label} browser errors:\n" + "\n".join(errors)
    print(f"{label}: routes/console/assets/responsive PASS")


def demo_deep_links(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors: list[str] = []
    attach_error_capture(page, errors)
    for anchor in DEMO_HASHES:
        response = page.goto(f"{BASE}/operator-intelligence#{anchor}", wait_until="networkidle", timeout=45_000)
        assert response is not None and response.status < 400, anchor
        page.wait_for_timeout(150)
        assert page.locator("body").inner_text().strip(), anchor
    text = page.locator("body").inner_text()
    assert "FICTIONAL DEMO DATA" in text
    assert "$392,570.56" in text
    assert "Verified Value" in text
    context.close()
    assert not errors, "demo browser errors:\n" + "\n".join(errors)
    print("Demo deep links and financial smoke: PASS")


def main() -> None:
    wait_for_preview()
    check_headers()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for label, viewport in VIEWPORTS:
                visit(browser, label, viewport)
            demo_deep_links(browser)
        finally:
            browser.close()
    print("STABILIS DEPLOY PREVIEW BROWSER QA = PASS")


if __name__ == "__main__":
    main()
