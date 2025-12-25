#!/bin/bash
# Start ML collector in background using nohup
# Works without systemd (for WSL2 without systemd enabled)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"
LOG_FILE="${HOME}/.poe_price_checker/ml-collector.log"
PID_FILE="${HOME}/.poe_price_checker/ml-collector.pid"

# Create log directory
mkdir -p "$(dirname "${LOG_FILE}")"

# Check if already running
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "ML collector is already running (PID: ${OLD_PID})"
        echo "Use ./scripts/ml-collector-stop.sh to stop it first"
        exit 1
    else
        rm -f "${PID_FILE}"
    fi
fi

echo "Starting ML collector..."
echo "  Log file: ${LOG_FILE}"
echo "  PID file: ${PID_FILE}"

cd "${REPO_DIR}"

# Start in background with nohup
nohup "${REPO_DIR}/.venv/bin/python" -c "
import logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
from ml.collection.orchestrator import MLCollectionOrchestrator
orch = MLCollectionOrchestrator()
orch.start()
import threading
threading.Event().wait()
" >> "${LOG_FILE}" 2>&1 &

# Save PID
echo $! > "${PID_FILE}"

echo
echo "ML collector started (PID: $(cat "${PID_FILE}"))"
echo
echo "To view logs:  tail -f ${LOG_FILE}"
echo "To stop:       ./scripts/ml-collector-stop.sh"
