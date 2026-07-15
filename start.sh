#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Install deps if needed
if [ ! -f ".backend_deps_installed" ]; then
    echo "[INFO] Installing Python dependencies..."
    pip install -r requirements.txt -q
    touch .backend_deps_installed
    echo "[OK] Dependencies installed"
fi

echo "[INFO] Starting ComplianceAudit Backend on port 8000 ..."
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
