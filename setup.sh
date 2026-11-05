#!/usr/bin/env bash
# LotusKey - Setup Launcher
# Author: Victor Pham
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# If --silent or -s is passed, run in silent mode
if [[ "$*" == *"--silent"* ]] || [[ "$*" == *"-s"* ]] || [[ "$*" == *"--quiet"* ]]; then
    python3 "$SCRIPT_DIR/ui/setup_wizard.py" --silent "$@"
    exit 0
fi

# If display is available, run GUI Wizard
if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    python3 "$SCRIPT_DIR/ui/setup_wizard.py" "$@"
else
    # Fallback to silent mode in non-graphical environment
    python3 "$SCRIPT_DIR/ui/setup_wizard.py" --silent "$@"
fi
