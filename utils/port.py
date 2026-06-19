"""Free a TCP port by stopping listeners (stdlib only; uses lsof on macOS/Linux)."""
import os
import signal
import subprocess
import time


def listeners_on_port(port: int) -> list[int]:
    """Return PIDs listening on *port*, or [] if none / lsof unavailable."""
    try:
        proc = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return sorted(set(pids))


def free_port(port: int, *, grace_seconds: float = 0.4) -> list[int]:
    """SIGTERM any process listening on *port* (except this one). Returns stopped PIDs."""
    me = os.getpid()
    stopped: list[int] = []
    for pid in listeners_on_port(port):
        if pid == me:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            stopped.append(pid)
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"  Could not stop PID {pid} on port {port} (permission denied).")
    if stopped:
        time.sleep(grace_seconds)
    return stopped
