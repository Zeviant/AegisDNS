"""Auto-starts the Dockerized backend when the native GUI launches, so a
non-technical user doesn't need to know `docker compose up -d` exists.

Requires Docker (Desktop or Engine) to already be installed and the daemon
running on the host — that part is a documented one-time setup step, not
something this module attempts to automate (installing Docker itself needs
admin rights / EULA acceptance / sometimes a reboot, none of which can be
driven silently). What this module *does* automate is everything after that:
finding the compose file, running `docker compose up -d`, and waiting for
the backend to answer /health before the GUI proceeds.
"""

import os
import subprocess
import time
from typing import Callable, Optional

from src.logic import api_client

# How long to wait for `docker compose up -d` to bring the backend up and
# answer /health. Generous on purpose: a first-ever run has to build the
# image (compiling llama-cpp-python takes several minutes on CPU); later
# runs just reuse the cached image and start in seconds.
STARTUP_TIMEOUT_S = 480
POLL_INTERVAL_S = 2


def _compose_dir() -> str:
    """Directory containing docker-compose.yml — the PyInstaller bundle when
    frozen (it's copied in alongside src/), the repo root in dev."""
    here = os.path.dirname(os.path.abspath(__file__))
    # src/logic/ -> repo root (or bundle root) is two levels up.
    return os.path.abspath(os.path.join(here, "..", ".."))


def is_docker_cli_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def ensure_backend_running(
    on_status: Optional[Callable[[str], None]] = None,
) -> tuple[bool, str]:
    """Best-effort: get the backend reachable at 127.0.0.1:5005.

    Returns (ok, message). On failure, message is meant to be shown directly
    to the user — it explains what to do, not a stack trace.
    """
    status = on_status or (lambda _msg: None)

    status("Checking backend...")
    if api_client.is_backend_reachable():
        return True, "Backend already running."

    status("Backend not running — checking Docker...")
    if not is_docker_cli_available():
        return False, (
            "AegisDNS's backend services run in Docker, but Docker isn't "
            "installed or isn't running on this machine.\n\n"
            "Install Docker Desktop (docker.com/products/docker-desktop), "
            "make sure it's running, then restart AegisDNS."
        )

    compose_dir = _compose_dir()
    compose_file = os.path.join(compose_dir, "docker-compose.yml")
    if not os.path.isfile(compose_file):
        return False, (
            "Could not find docker-compose.yml next to the application "
            f"(looked in: {compose_dir}).\n\n"
            "Reinstall AegisDNS, or start the backend manually."
        )

    status("Starting backend services (first run can take a few minutes)...")
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=STARTUP_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, (
            "Starting the backend timed out. Try running "
            "'docker compose up -d --build' manually from a terminal to see "
            "what's happening."
        )
    except OSError as e:
        return False, f"Failed to run 'docker compose': {e}"

    if result.returncode != 0:
        return False, (
            "Docker failed to start the backend:\n\n"
            f"{result.stderr.strip()[-800:]}"
        )

    status("Waiting for backend to come online...")
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if api_client.is_backend_reachable():
            return True, "Backend started."
        time.sleep(POLL_INTERVAL_S)

    return False, (
        "The backend container started but never became reachable at "
        "http://127.0.0.1:5005. Run 'docker compose logs backend' from a "
        "terminal to see what went wrong."
    )
