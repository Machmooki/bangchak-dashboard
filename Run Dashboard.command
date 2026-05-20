#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export DASHBOARD_HOME="$SCRIPT_DIR"
exec "$SCRIPT_DIR/system/Run Dashboard.command"
