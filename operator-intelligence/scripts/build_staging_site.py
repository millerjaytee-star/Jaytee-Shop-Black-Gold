"""Package a static review site for an approved, separate synthetic staging host."""

import json
import os
import re
from pathlib import Path
from shutil import copy2, copytree, rmtree
from tempfile import TemporaryDirectory
import tomllib

from scripts.build_site import PUBLIC_FILES, ROOT

STAGING = ROOT / "dist" / "staging"
PRODUCTION_API = "https://vpunfmwklwjefvchvmpn.supabase.co"
PRODUCTION_WEB = "https://stabilis-ops-group.netlify.app"
WEB_PATTERN = r"https://[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+"
API_PATTERN = r"https://[a-z0-9]{20}\.supabase\.co"
KEY_PATTERN = r"sb_publishable_[A-Za-z0-9_-]{16,}"
APPLE_PATTERN = r"[A-Z0-9]{10}\.com\.stabilisops\.operatorintelligence"


def build_staging(web: str, api: str, key: str, app_id: str = "", publish: Path = STAGING) -> None:
    if not re.fullmatch(WEB_PATTERN, web) or web == PRODUCTION_WEB or web.endswith("--stabilis-ops-group.netlify.app"):
        raise ValueError("Supply the HTTPS origin of a separate staging web site")
    if not re.fullmatch(API_PATTERN, api) or api == PRODUCTION_API:
        raise ValueError("Supply the HTTPS origin of a separate staging Supabase project")
    if not re.fullmatch(KEY_PATTERN, key):
        raise ValueError("Supply only the staging project's publishable key")
    if app_id and not re.fullmatch(APPLE_PATTERN, app_id):
        raise ValueError("Supply the verified Apple app identifier or leave it unset")

    settings = tomllib.loads((ROOT / "netlify.toml").read_text())
    publish.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=publish.parent, prefix="stabilis-stage-") as directory:
        target = Path(directory) / "site"
        target.mkdir()
        for file in PUBLIC_FILES:
            copy2(ROOT / file, target / file)
        copytree(ROOT / "assets", target / "assets")
        config = json.dumps({"supabaseUrl": api, "supabasePublishableKey": key, "staging": True})
        (target / "stabilis-config.js").write_text(
            f"window.STABILIS_CONFIG = Object.freeze(window.location.origin === {json.dumps(web)} "
            f"? {config} : {{ preview: true }});\n"
        )

        header_blocks = []
        for rule in settings["headers"]:
            values = dict(rule["values"])
            if rule["for"] == "/*":
                values["X-Robots-Tag"] = "noindex, nofollow, noarchive"
                values["Content-Security-Policy"] = (
                    values["Content-Security-Policy"].replace(PRODUCTION_API, api)
                    .replace("form-action 'self'", "form-action 'none'")
                )
            header_blocks.append("\n".join([rule["for"], *(f"  {name}: {value}" for name, value in values.items())]))
        (target / "_headers").write_text("\n\n".join(header_blocks) + "\n")

        with (target / "_redirects").open("a") as redirects:
            for rule in settings.get("redirects", []):
                redirects.write(f"\n{rule['from']}  {rule['to']}  {rule['status']}")
            redirects.write("\n")

        # This dedicated copy has no lead forms or function deploys.
        for name in ("index.html", "support.html"):
            page = target / name
            page.write_text(re.sub(r'\s+(?:data-netlify|netlify-honeypot)="[^"]+"', "", page.read_text()))

        if app_id:
            association = target / ".well-known" / "apple-app-site-association"
            association.parent.mkdir()
            association.write_text(json.dumps({"applinks": {"details": [{
                "appIDs": [app_id], "components": [{"/": "/mobile/review/*"}],
            }]}}) + "\n")
        if publish.exists():
            rmtree(publish)
        target.rename(publish)


if __name__ == "__main__":
    try:
        build_staging(
            os.environ.get("STABILIS_STAGING_WEB_ORIGIN", ""),
            os.environ.get("STABILIS_STAGING_SUPABASE_URL", ""),
            os.environ.get("STABILIS_STAGING_SUPABASE_PUBLISHABLE_KEY", ""),
            os.environ.get("STABILIS_STAGING_APPLE_APPLICATION_IDENTIFIER", ""),
        )
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(f"Built isolated synthetic staging site in {STAGING}")
