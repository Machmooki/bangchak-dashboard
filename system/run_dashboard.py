from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from app.project_paths import resolve_runtime_layout


LAYOUT = resolve_runtime_layout()
APP_HOME = LAYOUT.app_home
PROJECT_ROOT = LAYOUT.project_root
SYSTEM_DIR = LAYOUT.system_dir
REQUIREMENTS_FILE = SYSTEM_DIR / "requirements.txt"
HOST = "127.0.0.1"
START_PORT = 8000


def _module_is_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def ensure_pip() -> None:
    if getattr(sys, "frozen", False):
        return

    check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(APP_HOME),
        check=False,
    )
    if check.returncode == 0:
        return

    print("Bootstrapping pip for this Python installation...")
    subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"], cwd=str(APP_HOME))


def ensure_dependencies() -> None:
    if getattr(sys, "frozen", False):
        return

    missing = [module for module in ("fastapi", "uvicorn") if not _module_is_available(module)]
    if not missing:
        return

    ensure_pip()
    print("Installing missing dependencies...")
    command = [sys.executable, "-m", "pip", "install"]
    if sys.prefix == sys.base_prefix:
        command.append("--user")
    command.extend(["-r", str(REQUIREMENTS_FILE)])
    subprocess.check_call(
        command,
        cwd=str(APP_HOME),
    )


def find_available_port(start_port: int) -> int:
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available port found between 8000 and 8019.")


def wait_for_server_and_open_browser(url: str, port: int) -> None:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            try:
                sock.connect((HOST, port))
            except OSError:
                time.sleep(0.3)
                continue
        webbrowser.open(url)
        return


def main() -> None:
    ensure_dependencies()

    if str(SYSTEM_DIR) not in sys.path:
        sys.path.insert(0, str(SYSTEM_DIR))

    from app.main import app as dashboard_app
    import uvicorn

    port = find_available_port(START_PORT)
    url = f"http://{HOST}:{port}"

    print("=" * 60)
    print("Dashboard Bangchak")
    print(f"App folder    : {APP_HOME}")
    print(f"System folder : {SYSTEM_DIR}")
    print(f"Excel folder  : {PROJECT_ROOT / 'excel'}")
    print(f"Opening       : {url}")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)

    browser_thread = threading.Thread(
        target=wait_for_server_and_open_browser,
        args=(url, port),
        daemon=True,
    )
    browser_thread.start()

    uvicorn.run(dashboard_app, host=HOST, port=port, reload=False)


if __name__ == "__main__":
    main()
