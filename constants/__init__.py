"""Searay constants package.

Loads a local `.env` file (repo root) before any constant reads environment
variables, so secrets/config in `.env` are picked up automatically with a plain
`uv run` — no `--env-file` flag, no third-party dependency. Real environment
variables always win over `.env` values.
"""
import os


def _load_dotenv() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, ".env"), encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()
