#!/bin/bash
# Stop ML collector (works with both systemd and nohup)

SERVICE_NAME="poe-ml-collector"
PID_FILE="${HOME}/.poe_price_checker/ml-collector.pid"

# Try systemd first
if systemctl --user status "${SERVICE_NAME}" &>/dev/null; then
    echo "Stopping ML collector service (systemd)..."
    systemctl --user stop "${SERVICE_NAME}"
    echo "Service stopped."
    exit 0
fi

# Fall back to PID file (nohup mode)
if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        echo "Stopping ML collector (PID: ${PID})..."
        kill "${PID}"
        rm -f "${PID_FILE}"
        echo "Stopped."
    else
        echo "Process ${PID} not running. Cleaning up PID file."
        rm -f "${PID_FILE}"
    fi
else
    echo "ML collector is not running (no PID file found)."
fi
