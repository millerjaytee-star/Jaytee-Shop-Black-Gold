"""Exercise the real public forms with an in-memory inbox on loopback."""

import asyncio
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from functools import partial
from http.server import ThreadingHTTPServer
import os
from queue import Queue
from smtplib import SMTP as SMTPClient
from threading import Thread
from urllib.parse import parse_qs

from aiosmtpd.smtp import SMTP
from playwright.sync_api import expect, sync_playwright

from preview_site import PreviewHandler, ROOT


HOST = "127.0.0.1"
REQUESTER = "operator@example.test"
STAFF = "stabilis-support@example.test"
RELAY = "stabilis-forms@example.test"
CASES = (
    (
        "stabilis-pilot", "/#diagnostic", "/thanks", "Fit-call request received.",
        {
            "name": "Synthetic Operator", "email": REQUESTER, "company": "Fictional café",
            "locations": "3–15", "problem": "Synthetic weekly labor variance question.",
        },
        "Jaytee will reply to arrange a 20-minute fit call.",
    ),
    (
        "stabilis-support", "/support#account-deletion", "/support-received", "Support request received",
        {"email": REQUESTER, "topic": "account-deletion", "message": "Synthetic account deletion request."},
        "We received your request. We will verify your identity before processing it.",
    ),
)


class LocalInbox:
    def __init__(self):
        self.messages = Queue()

    async def handle_DATA(self, _server, _session, envelope):
        if envelope.rcpt_tos not in ([STAFF], [REQUESTER]):
            return "550 Only synthetic rehearsal recipients are allowed"
        message = BytesParser(policy=policy.default).parsebytes(envelope.original_content)
        self.messages.put(message)
        return "250 Captured in the local inbox"


def send(port, sender, recipient, subject, content, reply_to):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Reply-To"] = reply_to
    message["Subject"] = subject
    message.set_content(content)
    with SMTPClient(HOST, port, timeout=5) as smtp:
        smtp.send_message(message)


def rehearse_browser(base, inbox, port):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("STABILIS_CHROMIUM_PATH"), headless=True
        )
        try:
            for name, page_path, receipt, heading, fields, reply in CASES:
                page = browser.new_page(
                    viewport={"width": 390, "height": 844},
                    java_script_enabled=False,
                    reduced_motion="reduce",
                )
                confirmation = page.request.get(base + receipt)
                assert confirmation.ok, receipt
                captured = []

                def route_message(route):
                    request = route.request
                    if request.method == "GET" and request.url.startswith(base + "/"):
                        return route.continue_()
                    if request.method != "POST" or request.url != base + receipt:
                        return route.abort()
                    payload = parse_qs(request.post_data or "", keep_blank_values=True)
                    captured.append(payload)
                    expected = {"bot-field": [""], "form-name": [name], **{
                        key: [value] for key, value in fields.items()
                    }}
                    if payload != expected:
                        return route.fulfill(status=422, body="Rehearsal form payload differed from the fixture.")
                    send(port, RELAY, STAFF, name, "\n".join(fields.values()), REQUESTER)
                    return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=confirmation.body())

                page.route("**/*", route_message)
                page.goto(base + page_path)
                form = page.locator(f'form[name="{name}"]')
                expect(form).to_have_attribute("action", receipt)
                for key, value in fields.items():
                    field = form.locator(f'[name="{key}"]')
                    if key in {"locations", "topic"}:
                        field.select_option(value)
                    else:
                        field.fill(value)
                form.get_by_role("button").press("Enter")
                expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
                assert len(captured) == 1
                notice = inbox.messages.get(timeout=5)
                assert str(notice["To"]) == STAFF and str(notice["Subject"]) == name
                assert str(notice["Reply-To"]) == REQUESTER
                assert all(value in notice.get_content() for value in fields.values())

                send(port, STAFF, str(notice["Reply-To"]), f"Re: {name}", reply, STAFF)
                response = inbox.messages.get(timeout=5)
                assert str(response["To"]) == REQUESTER and str(response["From"]) == STAFF
                assert response.get_content().strip() == reply and inbox.messages.empty()
                page.close()
                print(f"{name}: browser receipt, local SMTP capture and reply passed", flush=True)
        finally:
            browser.close()


async def main():
    inbox = LocalInbox()
    relay = await asyncio.get_running_loop().create_server(lambda: SMTP(inbox), HOST, 0)
    port = relay.sockets[0].getsockname()[1]
    with ThreadingHTTPServer((HOST, 0), partial(PreviewHandler, directory=str(ROOT))) as site:
        worker = Thread(target=site.serve_forever, daemon=True)
        worker.start()
        try:
            async with relay:
                await asyncio.to_thread(rehearse_browser, f"http://{HOST}:{site.server_port}", inbox, port)
        finally:
            site.shutdown()
            worker.join()


if __name__ == "__main__":
    asyncio.run(main())
