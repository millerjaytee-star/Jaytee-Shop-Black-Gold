"""Exercise the real browser XLSX reader against a fictional three-sheet workbook."""
from base64 import b64encode
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import os
from pathlib import Path
from threading import Thread
from zipfile import ZIP_DEFLATED, ZipFile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "tests" / "fixtures" / "labor-reports-example.xlsx"


def rewrite_part(parts):
    revised = BytesIO()
    with ZipFile(EXAMPLE) as source, ZipFile(revised, "w", ZIP_DEFLATED) as dest:
        for name in source.namelist():
            contents = source.read(name)
            if name in parts:
                before, after = parts[name]
                assert before in contents
                contents = contents.replace(before, after, 1)
            dest.writestr(name, contents)
    return revised.getvalue()


def test_browser_reads_sheets_cached_formulas_dates_and_limits():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get("STABILIS_BROWSER_EXECUTABLE")
            browser = playwright.chromium.launch(executable_path=executable, args=["--no-sandbox"])
            page = browser.new_page()
            # Use a minimal same-origin page; the parser runs client-side against uploaded bytes.
            url = f"http://127.0.0.1:{server.server_port}/"
            page.route(url, lambda route: route.fulfill(body="<!doctype html><title>XLSX fixture</title>", content_type="text/html"))
            page.goto(url)
            page.evaluate("""async () => {
                const { readXlsx } = await import('/assets/labor-import-xlsx.mjs');
                window.inspectXlsx = async bytes => {
                  const content = Uint8Array.from(atob(bytes), c => c.charCodeAt(0));
                  const book = await readXlsx(new File([content], 'weekly.xlsx'));
                  const sheets = {};
                  for (const name of book.names) sheets[name] = await book.rows(name);
                  return { names: book.names, date1904: book.date1904, sheets };
                };
                window.readXlsx = readXlsx;
            }""")

            def read(content):
                return page.evaluate("(bytes) => window.inspectXlsx(bytes)", b64encode(content).decode())

            original = read(EXAMPLE.read_bytes())
            assert original["names"] == ["Sales", "Schedule", "Payroll"]
            assert original["date1904"] is False
            sales = original["sheets"]["Sales"]
            assert sales[0] == ["Business date", "Location", "Net sales", "Forecast sales"]
            assert sales[1] == [46328, "Fictional café", 1100, 1400]
            assert [sum(row[i] for row in sales[1:]) for i in (2, 3)] == [9000, 10000]
            schedule = original["sheets"]["Schedule"]
            payroll = original["sheets"]["Payroll"]
            assert [sum(row[i] for row in schedule[1:]) for i in (3, 4)] == [125, 2500]
            assert [sum(row[i] for row in payroll[1:]) for i in (3, 4)] == [135, 2700]
            clock = rewrite_part({"xl/workbook.xml": (b"<workbookPr ", b'<workbookPr date1904="1" ')})
            assert read(clock)["date1904"] is True
            limits = page.evaluate("""async () => {
                try { await window.readXlsx(new Blob([new Uint8Array(5 * 1024 * 1024 + 1)])); }
                catch (error) { return error.message; }
            }""")
            assert "too large" in limits

            sparse = rewrite_part({"xl/worksheets/sheet1.xml": (b'<row r="8"', b'<row r="15001"')})
            error = page.evaluate("""bytes => window.inspectXlsx(bytes).then(() => '', err => err.message)""",
                                  b64encode(sparse).decode())
            assert "too large" in error
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
