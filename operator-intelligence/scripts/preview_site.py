"""Serve the Stabilis static site on loopback, honoring its Netlify routes and headers.

Run from any directory with Python 3.11+: python path/to/preview_site.py --port 8080
Netlify Functions and form submission processing belong to a hosted preview.
"""

import argparse
from fnmatch import fnmatchcase
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import tomllib
from urllib.parse import urlsplit, urlunsplit

from build_site import PREVIEW_BROWSER_CONFIG, ROOT, is_public_path

CONFIG = tomllib.loads((ROOT / "netlify.toml").read_text())


def routes() -> dict[str, tuple[str, int]]:
    redirects = {}
    for line in (ROOT / "_redirects").read_text().splitlines():
        fields = line.split()
        if fields and not fields[0].startswith("#"):
            source, destination, status = fields[:3]
            redirects[source] = (destination, int(status.rstrip("!")))
    for rule in CONFIG.get("redirects", []):
        redirects.setdefault(rule["from"], (rule["to"], rule["status"]))
    return redirects


ROUTES = routes()


class PreviewHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        requested = urlsplit(self.path)
        self.requested_path = requested.path
        if requested.path == "/stabilis-config.js":
            content = PREVIEW_BROWSER_CONFIG.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            return BytesIO(content)
        target, status = ROUTES.get(requested.path, (requested.path, 200))
        if status in (301, 302, 307, 308):
            self.send_response(status)
            url = urlsplit(target)
            self.send_header("Location", urlunsplit(("", "", url.path, requested.query or url.query, url.fragment)))
            self.end_headers()
            return None
        self.path = target
        resolved = Path(self.translate_path(target)).resolve()
        if resolved == ROOT:
            resolved = ROOT / "index.html"
        elif resolved.suffix == "" and resolved.with_suffix(".html").is_file():
            resolved = resolved.with_suffix(".html")
        if not resolved.is_relative_to(ROOT) or not is_public_path(resolved) or not resolved.is_file():
            self.send_error(404)
            return None
        self.path = "/" + resolved.relative_to(ROOT).as_posix()
        return super().send_head()

    def end_headers(self):
        requested = getattr(self, "requested_path", urlsplit(self.path).path)
        headers = {}
        for rule in CONFIG.get("headers", []):
            if fnmatchcase(requested, rule["for"]):
                headers.update(rule["values"])
        for name, value in headers.items():
            self.send_header(name, value)
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(PreviewHandler, directory=str(ROOT))) as server:
        print(f"Stabilis local preview: http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()
