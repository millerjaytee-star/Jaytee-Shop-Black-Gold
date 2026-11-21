import json

import pytest

from scripts.build_staging_site import PRODUCTION_API, PRODUCTION_WEB, build_staging


WEB = "https://stabilis-testing.example"
API = "https://abcdefghijklmnopqrst.supabase.co"
KEY = "sb_publishable_synthetic_fixture"
APP_ID = "TESTTEAM01.com.stabilisops.operatorintelligence"


def test_staging_package_targets_only_the_approved_origin(tmp_path):
    site = tmp_path / "staging"
    build_staging(WEB, API, KEY, APP_ID, site)

    config = (site / "stabilis-config.js").read_text()
    assert API in config and KEY in config and WEB in config
    assert "window.location.origin ===" in config
    assert PRODUCTION_API not in config
    headers = (site / "_headers").read_text()
    assert f"connect-src 'self' {API}" in headers
    assert "form-action 'none'" in headers
    assert "X-Robots-Tag: noindex" in headers
    assert "/mobile/review/*" in (site / "_redirects").read_text()
    assert "/resources" in (site / "_redirects").read_text()
    for page in ("index.html", "support.html"):
        assert "data-netlify=" not in (site / page).read_text()
    association = json.loads((site / ".well-known/apple-app-site-association").read_text())
    assert association["applinks"]["details"] == [{
        "appIDs": [APP_ID], "components": [{"/": "/mobile/review/*"}],
    }]
    for name in ("netlify.toml", "netlify", "operator-intelligence", "ios", "docs"):
        assert not (site / name).exists()


@pytest.mark.parametrize("web, api, key, app_id", [
    (PRODUCTION_WEB, API, KEY, ""),
    ("https://deploy-preview-15--stabilis-ops-group.netlify.app", API, KEY, ""),
    (WEB, PRODUCTION_API, KEY, ""),
    (WEB, API, "sb_secret_synthetic_fixture", ""),
    (WEB, API + "/auth/v1", KEY, ""),
    (WEB, API, KEY, "unverified"),
])
def test_staging_requires_separate_origins_and_public_key(tmp_path, web, api, key, app_id):
    site = tmp_path / "staging"
    with pytest.raises(ValueError):
        build_staging(web, api, key, app_id, site)
    assert not site.exists()


def test_staging_password_recovery_uses_the_matching_web_origin(tmp_path):
    import mimetypes
    import os
    from pathlib import Path
    from urllib.parse import parse_qs, urlsplit

    from playwright.sync_api import expect, sync_playwright

    site = tmp_path / "staging"
    build_staging(WEB, API, KEY, publish=site)
    policy = next(
        line.strip().split(": ", 1)[1]
        for line in (site / "_headers").read_text().splitlines()
        if line.strip().startswith("Content-Security-Policy:")
    )
    recovery = []

    def fixture(route):
        request = route.request
        url = urlsplit(request.url)
        origin = f"{url.scheme}://{url.netloc}"
        if origin == API:
            assert request.method == "POST" and url.path == "/auth/v1/recover"
            recovery.append((parse_qs(url.query), request.post_data_json))
            route.fulfill(status=200, json={}, headers={"Access-Control-Allow-Origin": WEB})
            return
        if origin not in (WEB, PRODUCTION_WEB):
            route.abort()
            return
        path = site / (url.path.lstrip("/") or "index.html")
        if path.name == "login":
            path = path.with_suffix(".html")
        if not path.is_file():
            route.fulfill(status=404, body="")
            return
        route.fulfill(path=path, content_type=mimetypes.guess_type(path.name)[0],
                      headers={"Content-Security-Policy": policy})

    with sync_playwright() as driver:
        executable = os.environ.get("STABILIS_BROWSER_EXECUTABLE")
        if not executable and not Path(driver.chromium.executable_path).exists():
            pytest.skip("Chromium is required to exercise the browser staging package")
        with driver.chromium.launch(executable_path=executable) as browser:
            page = browser.new_page()
            page.route("**/*", fixture)
            page.goto(f"{WEB}/login")
            page.get_by_label("Work email").fill("operator@fixture.invalid")
            page.get_by_role("button", name="Send password reset email").click()
            expect(page.locator("#status")).to_contain_text("a reset message has been sent")
            assert recovery == [({"redirect_to": [f"{WEB}/login"]}, {"email": "operator@fixture.invalid"})]

            page.goto(f"{PRODUCTION_WEB}/login")
            expect(page.locator("#previewLogin")).to_be_visible()
            expect(page.get_by_role("button", name="Send password reset email")).to_be_hidden()
            assert len(recovery) == 1
