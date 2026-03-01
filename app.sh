#!/usr/bin/env bash
clear
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"
fi

source "$VENV_DIR/bin/activate"
export NODE_NO_WARNINGS=1

python "$SCRIPT_DIR/main.py"
