"""Use actual CSV and XLSX files in the public weekly review, then reload the persisted result."""
from functools import partial
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import sys
from threading import Thread

from playwright.sync_api import expect, sync_playwright
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from preview_site import PreviewHandler, ROOT

EXAMPLES = ROOT / "assets" / "labor-examples"
STORAGE = "stabilis-fictional-labor-review-v1"


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_map_and_save_three_daily_reports(extension):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(PreviewHandler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("STABILIS_BROWSER_EXECUTABLE"),
                                        args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto(f"http://127.0.0.1:{server.server_port}/labor-review")
            page.select_option("select[name=demo-role]", "STABILIS_ANALYST")
            page.locator("[data-new]").click()
            form = page.locator("form[data-op=create]")
            form.locator("input[name=week_start]").fill("2026-10-26")
            form.locator("[data-reconcile]").click()
            for kind in ["sales", "schedule", "payroll"]:
                part = page.locator(f'[data-report="{kind}"]')
                path = EXAMPLES / (kind + ".csv" if extension == "csv" else "weekly-reports.xlsx")
                part.locator("input[type=file]").set_input_files(path)
                expect(part.locator("[data-field=date]")).to_be_visible()
                if extension == "xlsx":
                    part.locator("[data-sheet]").select_option(kind.title())
                    expect(part.locator("[data-location-value]")).to_have_value("Juniper Café")
            page.locator("[data-preview]").click()
            page.locator("[data-apply]").click()
            expect(form.locator("input[name=actual_sales]")).to_have_value("9000")
            expect(form.locator("input[name=scheduled_hours]")).to_have_value("125")
            expect(form.locator("input[name=actual_hours]")).to_have_value("135")
            form.locator('input[name="target_pct"]').fill("25")
            form.get_by_role("button", name="Confirm and save baseline").click()
            expect(page.locator(".lr-message")).to_have_text("Baseline saved.")
            page.reload()
            week = page.evaluate("(key) => JSON.parse(localStorage.getItem(key)).reviews.find("
                                 "r=>r.week_start==='2026-10-26')", STORAGE)
            assert [week["metrics"][k] for k in ("total_over", "sales_effect", "payroll_effect")] == [450, 250, 200]
            assert "14 rows (7/7d)" in week["source"]
            if extension == "xlsx":
                assert "weekly-reports.xlsx" in week["source"] and "Payroll r1" in week["source"]
            else:
                assert "payroll.csv" in week["source"] and "schedule.csv" in week["source"]
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
