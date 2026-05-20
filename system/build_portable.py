from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from app.project_paths import resolve_project_root


SOURCE_HOME = Path(__file__).resolve().parent
BUILD_ROOT = SOURCE_HOME / "build"
SPEC_ROOT = SOURCE_HOME / ".tmp" / "pyinstaller-spec"
APP_SOURCE = SOURCE_HOME / "app"
DIST_ROOT = SOURCE_HOME / "dist" / "Dashboard Bangchak"
PROJECT_ROOT = resolve_project_root(SOURCE_HOME)
EXCEL_SOURCE = PROJECT_ROOT / "excel"


def ensure_packager() -> None:
    if importlib.util.find_spec("PyInstaller") is not None:
        return

    print("Installing PyInstaller...")
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(SOURCE_HOME),
        check=False,
    )
    if pip_check.returncode != 0:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"], cwd=str(SOURCE_HOME))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=str(SOURCE_HOME))


def run_pyinstaller() -> None:
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    if SPEC_ROOT.exists():
        shutil.rmtree(SPEC_ROOT)

    SPEC_ROOT.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--contents-directory",
        "system",
        "--name",
        "Dashboard Bangchak",
        "--specpath",
        str(SPEC_ROOT),
        "--paths",
        str(SOURCE_HOME),
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "fastapi",
        "--collect-all",
        "starlette",
        "--collect-all",
        "websockets",
        "--add-data",
        f"{APP_SOURCE};app",
        "run_dashboard.py",
    ]
    subprocess.check_call(command, cwd=str(SOURCE_HOME))

    stale_root_spec = SOURCE_HOME / "Dashboard Bangchak.spec"
    if stale_root_spec.exists():
        stale_root_spec.unlink()


def copy_runtime_content() -> None:
    excel_target = DIST_ROOT / "excel"
    if excel_target.exists():
        shutil.rmtree(excel_target)
    shutil.copytree(EXCEL_SOURCE, excel_target)

    launcher_target = DIST_ROOT / "Run Dashboard.bat"
    launcher_target.write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "start \"\" \"Dashboard Bangchak.exe\"\r\n",
        encoding="utf-8",
    )

    mac_launcher_target = DIST_ROOT / "Run Dashboard.command"
    mac_launcher_target.write_text(
        "#!/bin/bash\n"
        "cd \"$(dirname \"$0\")\"\n"
        "echo \"This portable package is for Windows only.\"\n"
        "echo \"For macOS, use the source package and run Run Dashboard.command there.\"\n",
        encoding="utf-8",
    )

    readme_target = DIST_ROOT / "README-Portable.txt"
    readme_target.write_text(
        "Portable package\r\n"
        "================\r\n\r\n"
        "1. Keep the folder structure as-is.\r\n"
        "2. Put Excel files in the excel folder.\r\n"
        "3. Double-click 'Dashboard Bangchak.exe' or 'Run Dashboard.bat'.\r\n",
        encoding="utf-8",
    )


def main() -> None:
    ensure_packager()
    run_pyinstaller()
    copy_runtime_content()
    print(f"Portable build ready at: {DIST_ROOT}")


if __name__ == "__main__":
    main()
