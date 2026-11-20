"""Browser-to-PostgreSQL contract for private weekly reviews with synthetic identities.

The app, migration, records and role enforcement run normally. Only the external
Supabase auth/REST transport and existing workspace bootstrap are replaced locally.
Set STABILIS_BROWSER_EXECUTABLE to select a system Chromium when needed.
"""

from functools import partial
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
import pytest

import test_postgres_labor_review as postgres_fixture
from test_postgres_labor_review import (
    ANALYST,
    GM,
    LOCATION,
    ORG,
    OUTSIDE,
    OTHER_ORG,
    OUTSIDE_LOCATION,
    OWNER,
    VIEWER,
    literal,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from preview_site import PreviewHandler, ROOT

db = postgres_fixture.db

USERS = {
    "analyst": (ANALYST, "STABILIS_ANALYST"),
    "owner": (OWNER, "OWNER_EXECUTIVE"),
    "gm": (GM, "GENERAL_MANAGER"),
    "viewer": (VIEWER, "READ_ONLY"),
    "outside": (OUTSIDE, "OWNER_EXECUTIVE"),
}
RPC_ARGS = {
    "stabilis_enroll_labor_assignee": ("p_organization_id", "p_location_id", "p_name"),
    "stabilis_labor_assignees": ("p_organization_id", "p_location_id"),
    "stabilis_labor_reviews": ("p_organization_id", "p_location_id"),
    "stabilis_save_labor_review": (
        "p_organization_id",
        "p_location_id",
        "p_review_id",
        "p_version",
        "p_operation",
        "p_payload",
    ),
}


def browser_transport(route, address, database):
    request = route.request
    url = urlsplit(request.url)
    if url.netloc != urlsplit(address).netloc:
        return route.abort()
    if url.path == "/stabilis-config.js":
        return route.fulfill(
            content_type="application/javascript",
            body="window.STABILIS_CONFIG="
            + json.dumps({"supabaseUrl": address + "/db", "supabasePublishableKey": "test-only"})
            + ";",
        )
    if not url.path.startswith("/db/"):
        return route.continue_()
    name = request.headers.get("authorization", "").removeprefix("Bearer synthetic-")
    action = url.path.removeprefix("/db/")
    values = request.post_data_json or {}
    if action == "auth/v1/token":
        name = values.get("email", "").split("@")[0]
        if name not in USERS or values.get("password") != "fixture-credential":
            return route.fulfill(status=401, json={"message": "Unknown test identity"})
        return route.fulfill(json={"access_token": "synthetic-" + name, "expires_in": 3600})
    if name not in USERS:
        return route.fulfill(status=403, json={"message": "Synthetic session required"})
    actor, role = USERS[name]
    org = OTHER_ORG if actor == OUTSIDE else ORG
    location = OUTSIDE_LOCATION if actor == OUTSIDE else LOCATION
    if action == "auth/v1/user":
        return route.fulfill(json={"id": actor, "email": name + "@fixture.invalid"})
    if action == "auth/v1/logout":
        return route.fulfill(status=204, body="")
    if action == "rest/v1/stabilis_my_organizations":
        return route.fulfill(json=[{"id": org, "name": "QA Organization", "slug": "qa", "role": role}])
    if action == "rest/v1/stabilis_my_locations":
        return route.fulfill(json=[{"id": location, "organization_id": org, "name": "Test café", "code": "QA"}])
    function = action.removeprefix("rest/v1/rpc/")
    if function == "stabilis_workspace_payload":
        return route.fulfill(
            json={
                "context": {"role": role},
                "kpis": {},
                "locations": [],
                "opportunities": [],
                "actions": [],
                "alerts": [],
                "reports": [],
                "data_quality_issues": [],
            }
        )
    if function == "stabilis_record_usage_event":
        return route.fulfill(json=True)
    if function not in RPC_ARGS:
        return route.fulfill(status=404, json={"message": "Unknown local RPC"})

    def parameter(value):
        if value is None:
            return "null"
        if isinstance(value, dict):
            return literal(json.dumps(value)) + "::jsonb"
        return literal(value)

    args = ",".join(parameter(values[key]) for key in RPC_ARGS[function])
    try:
        result = database.run(f"select public.{function}({args})", actor=actor)
        return route.fulfill(content_type="application/json", body=json.dumps(result))
    except AssertionError as exc:
        return route.fulfill(status=400, json={"message": str(exc).splitlines()[0]})


@pytest.fixture
def local_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(PreviewHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_private_weekly_cycle(db, local_site):
    with sync_playwright() as driver:
        executable = os.environ.get("STABILIS_BROWSER_EXECUTABLE")
        if not executable and not Path(driver.chromium.executable_path).exists():
            pytest.skip("Chromium needed for local private review browser test")
        browser = driver.chromium.launch(
            executable_path=executable, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        errors = []
        pages = {}

        def enter(name):
            context = browser.new_context(viewport={"width": 390 if name == "gm" else 1280, "height": 900})
            context.route("**/*", lambda route: browser_transport(route, local_site, db))
            page = context.new_page()
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            direct_link = name in {"analyst", "gm"}
            page.goto(local_site + ("/app#labor-review" if direct_link else "/app"))
            expect(page).to_have_url(local_site + ("/login?view=labor-review" if direct_link else "/login"))
            page.locator("#email").fill(name + "@fixture.invalid")
            page.locator("#password").fill("fixture-credential")
            page.locator("#loginForm button").click()
            page.wait_for_url(local_site + ("/app#labor-review" if direct_link else "/app"))
            if not direct_link:
                page.locator('a[href="#labor-review"]:visible').first.click()
            location = OUTSIDE_LOCATION if name == "outside" else LOCATION
            page.locator("#locationSelect").select_option(location)
            expect(page.locator("[data-labor-private] [data-refresh]")).to_be_visible()
            pages[name] = page
            return page

        def operation(page, name, fields=None):
            form = page.locator(f'form[data-op="{name}"]')
            for key, value in (fields or {}).items():
                control = form.locator('[name="' + key + '"]')
                if control.evaluate("el => el.tagName") == "SELECT":
                    control.select_option(str(value))
                else:
                    control.fill(str(value))
            form.locator('[type="submit"]').click()

        def refresh(page):
            page.locator("[data-refresh]").click()
            expect(page.locator(".lr-message")).to_have_text("Review is up to date.")

        try:
            analyst = enter("analyst")
            gm = enter("gm")
            owner = enter("owner")
            viewer = enter("viewer")
            outside = enter("outside")
            gm.get_by_text("Join this location’s GM roster", exact=True).click()
            operation(gm, "enroll", {"name": "Morgan · fixture GM"})
            expect(gm.locator(".lr-message")).to_have_text("GM roster updated.")
            analyst.locator("[data-new]").click()
            baseline = analyst.locator('[data-op="create"]')
            baseline.locator("summary").click()
            baseline.locator("input[type=file]").set_input_files(str(ROOT / "assets/labor-review-example.csv"))
            expect(baseline.locator('[name="actual_cost"]')).to_have_value("2700")
            # Independent from the months used in the SQL tests.
            baseline.locator('[name="week_start"]').fill("2026-10-05")
            operation(analyst, "create")
            expect(analyst.locator(".lr-big")).to_have_text("$450")
            expect(analyst.get_by_text("$250", exact=True)).to_be_visible()
            expect(analyst.get_by_text("$200", exact=True)).to_be_visible()
            refresh(owner)
            expect(owner.get_by_text("Week of Oct 5, 2026")).to_have_count(0)
            operation(analyst, "release", {"note": "Agreed weekly sales, payroll and schedule totals."})
            expect(analyst.locator(".lr-message")).to_have_text("Analyst released finding.")
            refresh(owner)
            operation(
                owner,
                "assign",
                {
                    "title": "Review closing coverage",
                    "assignee_id": GM,
                    "due_date": "2026-10-13",
                    "next_review": "2026-10-16",
                },
            )
            expect(owner.locator(".lr-message")).to_have_text("Action assigned.")
            refresh(gm)
            operation(gm, "accept")
            expect(gm.locator(".lr-message")).to_have_text("GM accepted action.")
            operation(gm, "submit_evidence", {"note": "All seven closing schedules reconciled with paid hours."})
            expect(gm.locator(".lr-message")).to_have_text("GM submitted evidence.")
            refresh(viewer)
            expect(viewer.locator('[data-op="compare"]')).to_have_count(0)
            expect(viewer.get_by_text("No finance validation", exact=True)).to_be_visible()
            refresh(owner)
            operation(
                owner,
                "compare",
                {
                    "week_start": "2026-10-12",
                    "forecast_sales": 10000,
                    "actual_sales": 9600,
                    "target_pct": 25,
                    "scheduled_hours": 125,
                    "actual_hours": 123,
                    "scheduled_cost": 2500,
                    "actual_cost": 2460,
                    "source": "Matched week payroll",
                    "comparable": "yes",
                    "note": "Matched operating hours, sales and wage rates.",
                },
            )
            expect(owner.get_by_text("$390", exact=True)).to_be_visible()
            expect(owner.get_by_text("No finance validation", exact=True)).to_be_visible()
            owner.locator("summary").filter(has_text="Record finance validation").click()
            operation(
                owner,
                "verify",
                {
                    "amount": 150,
                    "finance_reference": "QA finance 04",
                    "attribution": "Matched wage and closing coverage comparison",
                    "overlap_check": "Unique period, no other claims.",
                },
            )
            expect(owner.get_by_text("$150", exact=True)).to_be_visible()
            owner.reload()
            owner.locator("#locationSelect").select_option(LOCATION)
            expect(owner.get_by_text("$150", exact=True)).to_be_visible()
            expect(owner.get_by_text("Finance approval: QA finance 04.")).to_be_visible()
            refresh(outside)
            expect(outside.get_by_text("No weekly review available")).to_be_visible()
            expect(outside.get_by_text("$150", exact=True)).to_have_count(0)
            state = next(r for r in db.read(OWNER) if r["week_start"] == "2026-10-05")
            assert state["verification"]["amount"] == 150 and state["status"] == "verified"
            assert state["followup"]["observed_change"] == 390
            assert [x["operation"] for x in state["history"]] == [
                "create",
                "release",
                "assign",
                "accept",
                "submit_evidence",
                "compare",
                "verify",
            ]
            assert not errors, errors
        finally:
            browser.close()
