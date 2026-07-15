#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  ComplianceAudit Agent"
echo "============================================"
echo ""

# --- Check Python ---
if ! python3 --version &>/dev/null && ! python --version &>/dev/null; then
    echo "[ERROR] Python not found in PATH."
    echo "  Please install Python 3.10+."
    exit 1
fi

PYTHON=$(which python3 2>/dev/null || which python)
echo "[OK] Python detected: $PYTHON"

# --- Check opencode CLI ---
if ! command -v opencode &>/dev/null; then
    echo "[WARN] opencode CLI not found in PATH."
    echo "  Agent will run in simulation mode without AI."
    echo "  Install: pip install opencode"
    echo ""
fi

# --- Install deps (first run) ---
if [ ! -f ".deps_installed" ]; then
    echo "[INFO] Installing Python dependencies..."
    pip install -r requirements.txt -q 2>&1
    if [ $? -eq 0 ]; then
        touch .deps_installed
        echo "[OK] Dependencies installed"
    else
        echo "[WARN] pip install failed, please run manually:"
        echo "  pip install -r requirements.txt"
    fi
fi

echo ""
echo "  Config  : $SCRIPT_DIR/agent.yaml"
echo "  Skills  : $SCRIPT_DIR/compliance_skills/"
echo "  WorkDir : $SCRIPT_DIR"
echo ""
echo "[INFO] Starting Agent ..."
echo ""

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
$PYTHON -m agent.main
