#!/bin/bash
# Check ML collector status and recent logs (works with both systemd and nohup)

SERVICE_NAME="poe-ml-collector"
PID_FILE="${HOME}/.poe_price_checker/ml-collector.pid"
LOG_FILE="${HOME}/.poe_price_checker/ml-collector.log"

echo "=== ML Collector Status ==="
echo

# Check systemd first
if systemctl --user status "${SERVICE_NAME}" &>/dev/null; then
    echo "Running via: systemd"
    systemctl --user status "${SERVICE_NAME}" --no-pager
    echo
    echo "=== Recent Logs ==="
    journalctl --user -u "${SERVICE_NAME}" -n 20 --no-pager
else
    # Check PID file (nohup mode)
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        if kill -0 "${PID}" 2>/dev/null; then
            echo "Running via: nohup (PID: ${PID})"
            echo "Log file: ${LOG_FILE}"
        else
            echo "Status: NOT RUNNING (stale PID file)"
        fi
    else
        echo "Status: NOT RUNNING"
    fi

    if [ -f "${LOG_FILE}" ]; then
        echo
        echo "=== Recent Logs (last 20 lines) ==="
        tail -n 20 "${LOG_FILE}"
    fi
fi

echo
echo "=== Database Stats ==="
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
.venv/bin/python -c "
from core.database import Database
db = Database()
with db.transaction() as conn:
    runs = conn.execute('SELECT COUNT(*) FROM ml_collection_runs').fetchone()[0]
    listings = conn.execute('SELECT COUNT(*) FROM ml_listings').fetchone()[0]
    last_run = conn.execute('SELECT started_at FROM ml_collection_runs ORDER BY started_at DESC LIMIT 1').fetchone()
print(f'Total runs: {runs}')
print(f'Total listings: {listings}')
if last_run:
    print(f'Last run: {last_run[0]}')
" 2>/dev/null || echo "Could not query database"
