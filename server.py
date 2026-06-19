"""Searay Sales Assistant — JSON API engine (Python stdlib only).

Run:  uv run app                  (recommended — frees the port if needed)
      uv run python server.py

This serves the JSON API only. The rep UI is the Next.js frontend in `frontend/`
(`cd frontend && pnpm dev` → http://localhost:3000), which proxies its /api calls
here.

API:
  GET  /api/reasons                      -> rejection-reason chips
  GET  /api/customers                    -> customer cards
  GET  /api/customer/<code>              -> customer + current 3 actions
  POST /api/customer/<code>/feedback     -> {accepted:[id], rejections:[{id,reasons,note}]}
  POST /api/customer/<code>/reset        -> clear that customer's learning
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from constants.config import DEFAULT_PORT
from constants.customers import TARGET_CODES
from constants.feedback import RejectionReason
from utils.recommend import actions_payload, customer_list, reset, submit_feedback

PORT = int(os.environ.get("PORT", str(DEFAULT_PORT)))

# A small landing page so a browser hitting the engine port is pointed at the UI
# (rather than getting a bare 404).
ROOT_HTML = (
    "<!doctype html><meta charset=utf-8><title>Searay API</title>"
    "<body style='font-family:system-ui,-apple-system,sans-serif;max-width:34rem;"
    "margin:14vh auto;padding:0 1.2rem;color:#211d17;background:#f4efe6'>"
    "<h1 style='font-weight:800'>Searay Sales Assistant — API</h1>"
    "<p>This port serves the JSON API only. The rep app UI runs on the Next.js "
    "frontend:</p>"
    "<p style='font-size:1.1rem'><code>cd frontend &amp;&amp; pnpm dev</code> &nbsp;→&nbsp; "
    "<a href='http://localhost:3000' style='color:#9a6b1f;font-weight:700'>"
    "http://localhost:3000</a></p>"
    "<p style='color:#69736e'>Endpoints live under <code>/api/…</code></p></body>"
).encode("utf-8")


def reasons_payload():
    return [{"name": r.name, "icon": r.icon, "label": r.label, "help": r.help_text}
            for r in RejectionReason]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console quiet

    # --- helpers -----------------------------------------------------------
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _code_from(self, parts):
        code = parts[2] if len(parts) > 2 else ""
        return code if code in TARGET_CODES else None

    # --- routing -----------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._html(ROOT_HTML)
        if path == "/api/reasons":
            return self._json(reasons_payload())
        if path == "/api/customers":
            return self._json(customer_list())
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "customer":
            code = self._code_from(parts)
            return self._json(actions_payload(code)) if code else self.send_error(404)
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "customer":
            code = self._code_from(parts)
            if not code:
                return self.send_error(404)
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json({"error": "bad json"}, status=400)
            try:
                if parts[3] == "feedback":
                    return self._json(submit_feedback(
                        code, body.get("accepted", []), body.get("rejections", [])))
                if parts[3] == "reset":
                    return self._json(reset(code))
            except Exception as exc:  # never 500 silently in a demo
                return self._json({"error": str(exc)}, status=500)
        self.send_error(404)


def main():
    # Warm the engine so the first request is fast.
    customer_list()
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as exc:
        if exc.errno == 48:  # macOS EADDRINUSE
            print(f"\n  Port {PORT} is already in use (another server still running?).")
            print(f"  Or use:  uv run app   (auto-stops stale listeners)")
            print(f"  Or use another port:  PORT=8080 uv run app\n")
            raise SystemExit(1) from exc
        raise
    print(f"\n  Searay Sales Assistant — API engine")
    print(f"    API:  http://localhost:{PORT}/api/…")
    print(f"    UI:   cd frontend && pnpm dev   →   http://localhost:3000")
    print(f"\n  Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
