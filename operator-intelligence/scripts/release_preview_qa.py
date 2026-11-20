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

from playwright.sync_api import Browser, Page, Request as PlaywrightRequest, expect, sync_playwright

BASE = os.environ.get("STABILIS_RELEASE_BASE_URL", "").rstrip("/")
if not BASE:
    raise SystemExit("STABILIS_RELEASE_BASE_URL is required")

ROUTES = [
    "/",
    "/labor-review",
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


def ignorable_preview_console_error(text: str) -> bool:
    """Ignore only Netlify's injected preview-toolbar frame being blocked by our CSP."""
    return "Framing 'https://app.netlify.com/' violates" in text


def ignorable_navigation_abort(req: PlaywrightRequest) -> bool:
    """A route change may cancel an in-flight asset after the current page is already valid.

    Chromium reports that deliberate client cancellation as net::ERR_ABORTED. It is not an
    HTTP/network failure; HTTP >=400 responses and every other request failure remain fatal.
    """
    return req.url.startswith(BASE) and "net::ERR_ABORTED" in str(req.failure or "")


def attach_error_capture(page: Page, errors: list[str]) -> None:
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    def capture_console(msg) -> None:
        if msg.type == "error" and not ignorable_preview_console_error(msg.text):
            errors.append(f"console:{msg.type}: {msg.text}")

    def capture_request_failure(req: PlaywrightRequest) -> None:
        if not ignorable_navigation_abort(req):
            errors.append(f"requestfailed: {req.method} {req.url} {req.failure}")

    page.on("console", capture_console)
    page.on("requestfailed", capture_request_failure)
    page.on(
        "response",
        lambda resp: errors.append(f"asset-http-{resp.status}: {resp.url}")
        if resp.status >= 400 and resp.url.startswith(BASE) and resp.request.resource_type in {"script", "stylesheet", "image", "font"}
        else None,
    )


def check_home(page: Page, mobile: bool) -> None:
    chart = page.locator("#heroLab")
    expect(chart.locator("#laborGap")).to_have_text("$450")
    expect(chart.locator("#salesEffect")).to_have_text("$250")
    expect(chart.locator("#payrollEffect")).to_have_text("$200")
    chart.get_by_role("button", name="Week 2").click()
    expect(chart.locator("#laborGap")).to_have_text("$125")
    expect(chart.locator("#salesEffect")).to_have_text("$125")
    expect(chart.locator("#payrollEffect")).to_have_text("$0")
    expect(chart.locator("#laborPct")).to_have_text("26.3%")
    chart.get_by_role("button", name="Week 1").click()
    expect(chart.locator("#laborPct")).to_have_text("30.0%")

    if mobile:
        menu = page.get_by_role("button", name="Open navigation")
        menu.click()
        expect(page.locator("#siteNav")).to_be_visible()
        page.locator("#siteNav").get_by_role("link", name="Request a 20-minute fit call").click()
        assert page.url.endswith("#diagnostic")
    form = page.locator('form[name="stabilis-pilot"]')
    assert form.get_attribute("method").lower() == "post"
    expect(form.locator('select[name="locations"]')).to_have_value("")
    form.locator('select[name="locations"]').select_option(label="3–15")
    assert not form.evaluate("(form) => form.checkValidity()")

    sliders = page.locator("#score input[data-score]")
    expect(sliders).to_have_count(5)
    for slider in sliders.all():
        slider.fill("100")
    expect(page.locator("#scoreValue")).to_have_text("100")
    expect(page.locator("#scoreBand")).to_have_text("CONTROL STRONG")
    links = page.get_by_role("link", name="Try the labor review")
    assert links.count() >= 1
    for link in links.all():
        expect(link).to_have_attribute("href", "/labor-review")


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
        if path == "/":
            check_home(page, mobile=(label == "mobile"))
    context.close()
    assert not errors, f"{label} browser errors:\n" + "\n".join(errors)
    print(f"{label}: routes/console/assets/responsive PASS")


def demo_deep_links(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors: list[str] = []
    attach_error_capture(page, errors)
    response = page.goto(f"{BASE}/operator-intelligence#command", wait_until="networkidle", timeout=45_000)
    assert response is not None and response.status < 400
    for anchor in DEMO_HASHES:
        page.evaluate("anchor => { location.hash = anchor; }", anchor)
        page.wait_for_timeout(180)
        assert page.url.endswith(f"#{anchor}"), (anchor, page.url)
        assert page.locator("body").inner_text().strip(), anchor
    text = page.locator("body").inner_text()
    assert "FICTIONAL DEMO DATA" in text
    assert "$392,570.56" in text
    assert "Verified Value" in text
    context.close()
    assert not errors, "demo browser errors:\n" + "\n".join(errors)
    print("Demo deep links and financial smoke: PASS")


def labor_review_journey(browser: Browser) -> None:
    """Follow the fictional owner and GM through the same persisted review."""
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors: list[str] = []
    attach_error_capture(page, errors)
    writes = []
    page.on("request", lambda request: writes.append(request.method) if request.method != "GET" else None)
    page.goto(f"{BASE}/labor-review", wait_until="networkidle")
    role = page.locator('select[name="demo-role"]')
    expect(page.locator(".lr-big")).to_contain_text("$450")
    expect(page.locator(".lr-break")).to_contain_text("$250")
    expect(page.locator(".lr-break")).to_contain_text("$200")
    role.select_option("READ_ONLY")
    expect(page.locator('form[data-op="assign"]')).to_have_count(0)
    role.select_option("OWNER_EXECUTIVE")

    def submission(operation):
        return page.locator(f'form[data-op="{operation}"] [type="submit"]')

    title = "Review closing coverage with the shift lead"
    page.locator('[data-op="assign"] [name="title"]').fill(title)
    submission("assign").click()
    role.select_option("GENERAL_MANAGER")
    expect(page.get_by_text(title, exact=True)).to_be_visible()
    submission("accept").click()
    evidence = "QA example: shift lead matched all seven close schedules to paid hours."
    page.locator('[data-op="submit_evidence"] [name="note"]').fill(evidence)
    submission("submit_evidence").click()
    role.select_option("OWNER_EXECUTIVE")
    page.locator('[data-op="compare"] [name="comparable"]').select_option("yes")
    submission("compare").click()
    results = page.locator("section").filter(has=page.get_by_role("heading", name="Results", exact=True)).last
    expect(results).to_contain_text("$325")
    expect(results).to_contain_text("$0")
    expect(page.locator('form[data-op="verify"]')).to_have_count(1)
    page.reload(wait_until="networkidle")
    expect(results).to_contain_text("$325")
    expect(page.get_by_text(evidence, exact=True).first).to_be_visible()
    expect(page.locator('form[data-op="assign"]')).to_have_count(0)
    page.get_by_text("Record finance validation", exact=True).click()
    verify = page.locator('form[data-op="verify"]')
    verify.locator('[name="amount"]').fill("400")
    assert not verify.locator('[name="amount"]').evaluate("(input) => input.checkValidity()")
    verify.locator('[name="amount"]').fill("125")
    verify.locator('[name="finance_reference"]').fill("Fictional signed finance memo")
    verify.locator('[name="attribution"]').fill("Only supported hours included")
    verify.locator('[name="overlap_check"]').fill("Overtime excluded from this amount")
    submission("verify").click()
    expect(results).to_contain_text("Fictional signed finance memo")
    expect(results.locator("dt").get_by_text("Client-verified financial impact").locator("..")).to_contain_text("$125")
    page.emulate_media(media="print")
    expect(page.locator("[data-print]")).to_be_hidden()
    expect(results).to_be_visible()
    page.emulate_media(media="screen")

    # Import a second synthetic week with no forecast. Usable actuals survive,
    # and an unreleased analyst draft stays out of the owner's review list.
    role.select_option("STABILIS_ANALYST")
    page.get_by_role("button", name="New weekly review").click()
    create = page.locator('form[data-op="create"]')
    create.locator("summary").click()
    sample = b"week_start,actual_sales,target_pct,scheduled_hours,actual_hours,scheduled_cost,actual_cost,source\n2026-11-16,9000,25,125,135,2500,2700,QA fictional reports"
    create.locator('[data-csv]').set_input_files({"name":"sample.csv", "mimeType":"text/csv", "buffer":sample})
    expect(create.locator('[name="week_start"]')).to_have_value("2026-11-16")
    expect(create.locator('[name="forecast_sales"]')).to_have_value("")
    submission("create").click()
    expect(page.locator(".lr-break")).to_contain_text("Needs data")
    expect(page.locator(".lr-facts")).to_contain_text("10 h")
    role.select_option("OWNER_EXECUTIVE")
    expect(page.locator('select[name="review-id"] option')).to_have_count(1)
    role.select_option("STABILIS_ANALYST")
    page.locator('select[name="review-id"]').select_option(label="Nov 16, 2026")
    submission("release").click()
    role.select_option("OWNER_EXECUTIVE")
    expect(page.locator('select[name="review-id"] option')).to_have_count(2)
    assert not writes, "Fictional demo sent a write request"
    assert not errors, "weekly review browser errors:\n" + "\n".join(errors)
    context.close()
    print("Mobile owner–GM action, finance review, print, private draft and CSV intake: PASS")


def main() -> None:
    wait_for_preview()
    check_headers()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("STABILIS_CHROMIUM_PATH"), headless=True)
        try:
            for label, viewport in VIEWPORTS:
                visit(browser, label, viewport)
            demo_deep_links(browser)
            labor_review_journey(browser)
        finally:
            browser.close()
    print("STABILIS DEPLOY PREVIEW BROWSER QA = PASS")


if __name__ == "__main__":
    main()
