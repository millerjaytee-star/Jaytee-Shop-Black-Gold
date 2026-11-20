"""Create the deployable site from its existing HTML pages and public assets."""

import os
from pathlib import Path
from shutil import copy2, copytree, rmtree


ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / "dist/netlify"
PAGES = {
    "app.html", "control-room.html", "index.html", "labor-kds-workflow.html",
    "labor-review.html", "login.html", "new-store-operational-readiness.html",
    "off-premise-line-accuracy.html", "operator-intelligence-report.html",
    "operator-intelligence.html", "privacy.html", "profit-control-reset.html",
    "proof-ledger.html", "resources.html", "security.html", "terms.html", "thanks.html",
}
PUBLIC_FILES = PAGES | {"_redirects", "favicon.ico", "stabilis-config.js", "stabilis-release-marker.txt"}
PREVIEW_BROWSER_CONFIG = "window.STABILIS_CONFIG = Object.freeze({ preview: true });\n"


def is_public_path(file: Path) -> bool:
    relative = file.relative_to(ROOT)
    return relative.as_posix() in PUBLIC_FILES or relative.parts[:1] == ("assets",)


def build() -> None:
    if PUBLISH.exists():
        rmtree(PUBLISH)
    PUBLISH.mkdir(parents=True)
    for file in sorted(PUBLIC_FILES):
        copy2(ROOT / file, PUBLISH / file)
    if os.environ.get("CONTEXT") != "production":
        (PUBLISH / "stabilis-config.js").write_text(PREVIEW_BROWSER_CONFIG)
    copytree(ROOT / "assets", PUBLISH / "assets")
    print(f"Stabilis static site built in {PUBLISH}")


if __name__ == "__main__":
    build()
