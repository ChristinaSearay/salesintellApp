"""Start the rep web app, freeing the listen port first if occupied.

Run:  uv run app
"""
import os

from constants.config import DEFAULT_PORT
from utils.port import free_port


def main() -> None:
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    stopped = free_port(port)
    if stopped:
        labels = ", ".join(str(pid) for pid in stopped)
        print(f"\n  Port {port} was in use — stopped PID(s): {labels}\n")

    from server import main as serve

    serve()


if __name__ == "__main__":
    main()
