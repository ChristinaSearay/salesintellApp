"""Zero-dependency web server for the rep-facing GUI (Python stdlib only).

Run:  uv run app                  (recommended — frees the port if needed)
      uv run python server.py     then open http://localhost:8000 (or the LAN URL
it prints) on a phone on the same Wi-Fi.

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

from constants.config import BASE_DIR, DEFAULT_PORT
from constants.customers import TARGET_CODES
from constants.feedback import RejectionReason
from utils.recommend import actions_payload, customer_list, reset, submit_feedback

WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")
PORT = int(os.environ.get("PORT", str(DEFAULT_PORT)))

STATIC = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/app.js": "app.js",
}
CONTENT_TYPES = {".html": "text/html; charset=utf-8",
                 ".css": "text/css; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8"}


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

    def _file(self, name):
        path = os.path.join(WEBAPP_DIR, name)
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except FileNotFoundError:
            return self.send_error(404)
        ext = os.path.splitext(name)[1]
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _code_from(self, parts):
        code = parts[2] if len(parts) > 2 else ""
        return code if code in TARGET_CODES else None

    # --- routing -----------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in STATIC:
            return self._file(STATIC[path])
        # Any other top-level file in webapp/ (no subpaths -> no traversal).
        fname = path.lstrip("/")
        if fname and "/" not in fname and os.path.isfile(os.path.join(WEBAPP_DIR, fname)):
            return self._file(fname)
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
            print(f"\n  Port {PORT} is already in use (another server.py still running?).")
            print(f"  Or use:  uv run app   (auto-stops stale listeners)")
            print(f"  Or use another port:  PORT=8080 uv run app\n")
            raise SystemExit(1) from exc
        raise
    print(f"\n  Searay Sales Assistant running:")
    print(f"    On this computer:  http://localhost:{PORT}")
    print(f"    On your phone:     http://<this-computer's-LAN-IP>:{PORT}  (same Wi-Fi)")
    print(f"\n  Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
