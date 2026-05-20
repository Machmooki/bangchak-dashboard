#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${DASHBOARD_HOME:-}" ]; then
  DASHBOARD_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
export DASHBOARD_HOME

if [ -x ".venv/bin/python3" ] && ".venv/bin/python3" -m pip --version >/dev/null 2>&1; then
  exec ".venv/bin/python3" run_dashboard.py
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 run_dashboard.py
fi

osascript -e 'display dialog "Python 3 was not found on this Mac. Install Python 3.12+ first, then run Run Dashboard.command again." buttons {"OK"} default button "OK"' >/dev/null 2>&1 || true
echo "Python 3 was not found on this Mac."
echo "Install Python 3.12+ first, then run Run Dashboard.command again."
read -r -p "Press Enter to close..."
