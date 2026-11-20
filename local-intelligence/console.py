#!/usr/bin/env python3

import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import stabilis_local_ai


HOST = "127.0.0.1"
PORT = 8765


def page(question="", answer="", evidence=None, error=""):
    evidence = evidence or []

    evidence_html = ""
    if evidence:
        rows = []
        for item in evidence:
            score = html.escape(str(item.get("score", "")))
            source = html.escape(str(item.get("source", "")))
            chunk = html.escape(str(item.get("chunk", "")))
            rows.append(
                f"<tr><td>{score}</td><td>{source}</td><td>{chunk}</td></tr>"
            )

        evidence_html = f"""
        <section class="card">
          <h2>Retrieved Evidence</h2>
          <table>
            <thead>
              <tr><th>Score</th><th>Source</th><th>Chunk</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </section>
        """

    answer_html = ""
    if answer:
        answer_html = f"""
        <section class="card">
          <h2>Stabilis Answer</h2>
          <div class="answer">{html.escape(answer)}</div>
        </section>
        """

    error_html = ""
    if error:
        error_html = f"""
        <section class="card error">
          <h2>Local Engine Error</h2>
          <div>{html.escape(error)}</div>
        </section>
        """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stabilis Local Intelligence</title>
<style>
body {{
    margin: 0;
    background: #090909;
    color: #f4f1e8;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.shell {{
    max-width: 1000px;
    margin: auto;
    padding: 48px 24px;
}}
.brand {{
    color: #d8b65a;
    letter-spacing: .12em;
    font-size: 13px;
    font-weight: 700;
}}
h1 {{
    font-size: clamp(34px,6vw,62px);
    margin: 10px 0;
}}
.sub {{
    color: #aaa;
    margin-bottom: 32px;
}}
.badge {{
    display: inline-block;
    border: 1px solid #4c4327;
    color: #d8b65a;
    padding: 6px 10px;
    border-radius: 999px;
    margin-right: 6px;
    font-size: 12px;
}}
.card {{
    background: #111;
    border: 1px solid #282828;
    border-radius: 18px;
    padding: 24px;
    margin-top: 22px;
}}
textarea {{
    width: 100%;
    min-height: 110px;
    box-sizing: border-box;
    background: #080808;
    color: white;
    border: 1px solid #444;
    border-radius: 12px;
    padding: 16px;
    font-size: 17px;
}}
button {{
    margin-top: 14px;
    background: #d8b65a;
    color: #090909;
    border: 0;
    padding: 13px 22px;
    border-radius: 10px;
    font-weight: 800;
    cursor: pointer;
}}
.answer {{
    white-space: pre-wrap;
    line-height: 1.65;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
th, td {{
    text-align: left;
    padding: 10px;
    border-bottom: 1px solid #292929;
    vertical-align: top;
}}
th {{ color: #d8b65a; }}
.error {{ border-color: #713b3b; }}
.footer {{
    margin-top: 30px;
    color: #777;
    font-size: 13px;
}}
</style>
</head>

<body>
<div class="shell">

<div class="brand">STABILIS OPS GROUP</div>
<h1>Local Intelligence</h1>

<div class="sub">
Private operational intelligence grounded in Stabilis methodology.
</div>

<div>
<span class="badge">LOCAL</span>
<span class="badge">PRIVATE</span>
<span class="badge">QWEN3 4B</span>
<span class="badge">NOMIC</span>
</div>

<section class="card">
<h2>Ask Stabilis</h2>

<form method="POST">
<textarea
    name="question"
    placeholder="Ask an operational question..."
>{html.escape(question)}</textarea>

<button type="submit">Analyze</button>
</form>
</section>

{answer_html}
{evidence_html}
{error_html}

<div class="footer">
Runs on this Mac through Ollama. No OpenAI API request is required by this console.
</div>

</div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = page()
        self.respond(body)

    def do_POST(self):

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        question = parse_qs(raw).get("question", [""])[0].strip()

        if not question:
            self.respond(page(error="Enter a question first."))
            return

        try:
            records = stabilis_local_ai.load_knowledge()

            evidence = stabilis_local_ai.retrieve(
                question,
                records
            )

            answer = stabilis_local_ai.answer(
                question,
                evidence
            )

            self.respond(
                page(
                    question=question,
                    answer=answer,
                    evidence=evidence
                )
            )

        except Exception as exc:
            self.respond(
                page(
                    question=question,
                    error=f"{type(exc).__name__}: {exc}"
                )
            )

    def respond(self, text):
        data = text.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()

        self.wfile.write(data)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":

    print()
    print("STABILIS LOCAL INTELLIGENCE")
    print(f"Open: http://{HOST}:{PORT}")
    print("Press Control-C to stop.")
    print()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
