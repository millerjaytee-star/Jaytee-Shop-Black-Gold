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
