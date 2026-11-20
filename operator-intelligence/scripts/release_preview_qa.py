"""Browser-level release QA for the Stabilis Netlify deploy preview.

Runs against the real deploy-preview URL. It checks route rendering, browser console/page
errors, failed same-origin assets, security headers, desktop/tablet/mobile overflow, and
critical Operator Intelligence demo deep links. No customer credentials are used.
"""
from __future__ import annotations

import os
from pathlib import Path
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
    "/proof-ledger",
    "/control-room",
    "/resources",
    "/reset",
    "/thanks.html",
    "/support",
    "/support-received",
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
        menu = page.get_by_role("button", name="Open menu")
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


def keyboard_and_static_content(browser: Browser) -> None:
    context = browser.new_context(viewport=VIEWPORTS[-1][1])
    page = context.new_page()
    page.goto(BASE)
    page.keyboard.press("Tab")
    skip = page.get_by_role("link", name="Skip to content")
    expect(skip).to_be_focused()
    page.keyboard.press("Enter")
    assert page.url.endswith("#main")
    chart = page.locator("#heroLab")
    week = chart.get_by_role("button", name="Week 2")
    week.focus()
    page.keyboard.press("Enter")
    expect(week).to_have_attribute("aria-pressed", "true")
    expect(chart.locator("figcaption")).to_contain_text("26.3%")
    context.close()

    context = browser.new_context(viewport=VIEWPORTS[-1][1], java_script_enabled=False)
    page = context.new_page()
    page.goto(BASE)
    expect(page.get_by_role("heading", name="14-Day Margin Recovery Diagnostic")).to_be_visible()
    expect(page.get_by_text("$1,500", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Request a 20-minute fit call").first).to_be_visible()
    expect(page.get_by_role("link", name="Client login").first).to_be_visible()
    action = page.locator('form[name="stabilis-pilot"]').get_attribute("action")
    # Netlify Pretty URLs removes the .html suffix from the static form action.
    assert action in {"/thanks", "/thanks.html"}, action
    page.goto(BASE + action)
    expect(page.get_by_role("heading", name="Fit-call request received.")).to_be_visible()
    context.close()
    print("Mobile keyboard, chart text and static offer/contact: PASS")


def mobile_review_handoff(browser: Browser) -> None:
    page = browser.new_page(viewport=VIEWPORTS[-1][1])
    identifiers = [f"00000000-0000-4000-8000-{i:012d}" for i in range(1, 4)]
    organization, location, review = identifiers
    response = page.goto(BASE + "/mobile/review/" + "/".join(identifiers))
    assert response and response.ok
    assert "no-store" in response.headers.get("cache-control", "")
    expect(page.get_by_role("link", name="Open in the iPhone app")).to_have_attribute(
        "href", f"stabilis://review/{organization}/{location}/{review}",
    )
    expect(page.get_by_role("link", name="Open the web workspace")).to_have_attribute(
        "href", f"/app#labor-review/{location}/{review}",
    )
    page.get_by_role("link", name="Open the web workspace").click()
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()
    assert "labor-review%2F" in page.url
    page.close()
    print("Mobile review link preserves the authorized web destination: PASS")


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
    page.get_by_text("Show the math and source records", exact=True).click()
    expect(page.get_by_text("$2,700 − (25% × $9,000) = $450", exact=True)).to_be_visible()
    page.get_by_text("Show the math and source records", exact=True).click()
    scenario = page.locator("#labor-scenario")
    scenario_result = page.locator("#scenario-output")
    for case, total, explanation in [
        ("schedule", "$200", "Paid hours matched the schedule."),
        ("sales", "$250", "Sales finished $1,000 below forecast."),
        ("missing-forecast", "$450", "Add the sales forecast for this location and fiscal week"),
        ("varying-rates", "$125", "Paid hours matched the schedule."),
        ("zero-sales", "$2,700", "A labor percentage is undefined."),
    ]:
        scenario.select_option(case)
        expect(scenario_result.locator(".lr-big")).to_have_text(total)
        expect(scenario_result).to_contain_text(explanation)
    scenario.select_option("")
    role.select_option("READ_ONLY")
    expect(page.locator('form[data-op="assign"]')).to_have_count(0)
    expect(role).to_be_focused()
    role.select_option("OWNER_EXECUTIVE")

    def submission(operation):
        return page.locator(f'form[data-op="{operation}"] [type="submit"]')

    title = "Review closing coverage with the shift lead"
    page.locator('[data-op="assign"] [name="title"]').fill(title)
    submission("assign").click()
    role.select_option("GENERAL_MANAGER")
    page.reload(wait_until="networkidle")
    expect(role).to_have_value("GENERAL_MANAGER")
    expect(page.locator(".lr-grid h2").first).to_have_text("Action and follow-through")
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
    expect(results).to_contain_text("Labor variance improved by $325.")
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
    expect(scenario).to_be_hidden()
    expect(results).to_be_visible()
    page.emulate_media(media="screen")

    # Import a second synthetic week with no forecast. Usable actuals survive,
    # and an unreleased analyst draft stays out of the owner's review list.
    role.select_option("STABILIS_ANALYST")
    page.get_by_role("button", name="New weekly review").click()
    create = page.locator('form[data-op="create"]')
    create.locator("summary").click()
    sample = b"week_start,actual_sales,target_pct,scheduled_hours,actual_hours,scheduled_cost,actual_cost,source\n2026-10-26,9000,25,125,135,2500,2700,QA fictional reports"
    create.locator('[data-csv]').set_input_files({"name":"sample.csv", "mimeType":"text/csv", "buffer":sample})
    expect(create.locator('[name="week_start"]')).to_have_value("2026-10-26")
    expect(create.locator('[name="forecast_sales"]')).to_have_value("")
    submission("create").click()
    expect(page.locator(".lr-break")).to_contain_text("Needs data")
    expect(page.locator(".lr-facts")).to_contain_text("10 h")
    role.select_option("OWNER_EXECUTIVE")
    expect(page.locator('select[name="review-id"] option')).to_have_count(1)
    role.select_option("STABILIS_ANALYST")
    page.locator('select[name="review-id"]').select_option(label="Oct 26, 2026 · Analyst review")
    submission("release").click()
    role.select_option("OWNER_EXECUTIVE")
    expect(page.locator('select[name="review-id"] option')).to_have_count(2)
    assert not writes, "Fictional demo sent a write request"
    assert not errors, "weekly review browser errors:\n" + "\n".join(errors)
    context.close()
    print("Mobile owner–GM action, role persistence, variance cases, finance review, print, private draft and CSV intake: PASS")


def check_daily_import(browser: Browser) -> None:
    """Exercise the worksheet, date and location mapping used in the real review form."""
    fixture = Path(__file__).resolve().parents[2] / "assets/labor-examples/weekly-reports.xlsx"
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    attach_error_capture(page, errors)
    page.goto(f"{BASE}/labor-review", wait_until="networkidle")
    page.locator('select[name="demo-role"]').select_option("STABILIS_ANALYST")
    page.locator("[data-new]").click()
    form = page.locator('[data-op="create"]')
    form.locator("[data-reconcile]").click()
    dialog = page.get_by_role("dialog")
    dialog.locator("[data-week]").fill("2026-10-26")
    for report, sheet in [("sales", "Sales"), ("schedule", "Schedule"), ("payroll", "Payroll")]:
        part = dialog.locator(f'[data-report="{report}"]')
        part.locator("[data-file]").set_input_files(fixture)
        part.locator("[data-sheet]").select_option(label=sheet)
        part.locator("[data-location-value]").select_option(label="Juniper Café")
    dialog.locator("[data-preview]").click()
    expect(dialog.locator("[data-result]")).to_contain_text("2,700")
    expect(dialog.locator("[data-result]")).to_contain_text("2,500")
    expect(dialog.locator("[data-result]")).to_contain_text("9,000")
    assert dialog.evaluate("(el) => el.scrollWidth <= el.clientWidth + 2")
    dialog.locator("[data-apply]").click()
    expect(dialog).to_have_count(0)
    for field, value in [("forecast_sales", "10000"), ("actual_sales", "9000"),
                         ("scheduled_hours", "125"), ("actual_hours", "135"),
                         ("scheduled_cost", "2500"), ("actual_cost", "2700")]:
        expect(form.locator(f'[name="{field}"]')).to_have_value(value)
    reference = form.locator('[name="source"]').input_value()
    for sheet in ["Sales", "Schedule", "Payroll"]:
        assert sheet in reference
    assert not errors, errors
    page.close()
    print("Mobile multi-report XLSX mapping, totals and source references: PASS")


def check_control_room(browser: Browser) -> None:
    page = browser.new_page(viewport=VIEWPORTS[-1][1])
    page.goto(BASE)
    page.get_by_role("link", name="Open the local Control Room").click()
    page.get_by_role("button", name="Operating inputs").click()
    page.get_by_label("Location name").fill("Fictional training café")
    page.get_by_label("Net sales ($)").fill("9000")
    page.get_by_label("Loaded labor cost ($)").fill("2700")
    page.get_by_label("Labor target (%)").fill("25")
    page.get_by_role("button", name="Save location & diagnose").click()
    expect(page.locator(".hero-stat .stat-value")).to_have_text("$450")

    page.get_by_role("button", name="Data & reports").click()
    upload = page.get_by_label("Choose CSV file")
    upload.set_input_files({
        "name": "training.csv", "mimeType": "text/csv",
        "buffer": b"location,sales\nSecond training cafe,5000\n",
    })
    expect(page.locator("#notice")).to_contain_text("Imported 1 location")
    page.get_by_role("button", name="Save period snapshot").click()
    expect(page.locator("#snapshot-list").get_by_role("button")).to_have_count(1)
    page.reload()
    for name in ("Fictional training café", "Second training cafe"):
        expect(page.get_by_role("cell", name=name)).to_be_visible()
    page.close()
    print("Control Room manual entry, CSV append, snapshot and refresh: PASS")


def main() -> None:
    wait_for_preview()
    check_headers()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("STABILIS_CHROMIUM_PATH"), headless=True)
        try:
            for label, viewport in VIEWPORTS:
                visit(browser, label, viewport)
            keyboard_and_static_content(browser)
            mobile_review_handoff(browser)
            demo_deep_links(browser)
            labor_review_journey(browser)
            check_daily_import(browser)
            check_control_room(browser)
        finally:
            browser.close()
    print("STABILIS DEPLOY PREVIEW BROWSER QA = PASS")


if __name__ == "__main__":
    main()
