from __future__ import annotations

from pathlib import Path

from app.project_paths import resolve_runtime_layout


LAYOUT = resolve_runtime_layout()
APP_HOME = LAYOUT.app_home
PROJECT_ROOT = LAYOUT.project_root
SYSTEM_DIR = LAYOUT.system_dir
STATIC_DIR = LAYOUT.static_dir
EXCEL_DIR = LAYOUT.excel_dir


def discover_excel_file() -> Path:
    candidates = sorted(
        (
            path
            for path in EXCEL_DIR.glob("*.xlsx")
            if not path.name.startswith("~$")
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name.lower()),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No .xlsx file found in {EXCEL_DIR}.")
    return candidates[0]


EXCEL_FILE = discover_excel_file()
