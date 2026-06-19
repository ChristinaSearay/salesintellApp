"""Run the API engine and the Next.js rep UI together — one command.

Run:  uv run dev
      → API  on http://localhost:8000  (Python engine)
      → UI   on http://localhost:3000  (Next.js frontend)

Ctrl+C stops both. (Frontend deps must be installed once: `cd frontend && pnpm install`.)
"""
import os
import signal
import subprocess
import sys
import time

from constants.config import BASE_DIR, DEFAULT_PORT
from utils.port import free_port

UI_PORT = 3000


def main() -> None:
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    free_port(port)  # clear a stale engine listener if any

    frontend = os.path.join(BASE_DIR, "frontend")
    if not os.path.isdir(os.path.join(frontend, "node_modules")):
        print("\n  Frontend deps not installed — run once:  cd frontend && pnpm install\n")
        raise SystemExit(1)

    procs = []

    def shutdown(*_):
        # Each child runs in its own session, so kill the whole group
        # (so `next dev`'s child server goes too).
        for p in procs:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass

    signal.signal(signal.SIGTERM, lambda *_: (shutdown(), sys.exit(0)))

    try:
        procs.append(subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "server.py")],
            cwd=BASE_DIR, start_new_session=True))
        procs.append(subprocess.Popen(
            ["pnpm", "dev"],
            cwd=frontend, start_new_session=True))

        print(f"\n  Searay running — Ctrl+C to stop both:")
        print(f"    API:  http://localhost:{port}")
        print(f"    UI:   http://localhost:{UI_PORT}  (open this)\n")

        # If either process exits on its own, take the other down too.
        while all(p.poll() is None for p in procs):
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()
        for p in procs:
            try:
                p.wait(timeout=6)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
