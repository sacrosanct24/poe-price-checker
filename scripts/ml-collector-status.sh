#!/bin/bash
# Check ML collector service status and recent logs

SERVICE_NAME="poe-ml-collector"

echo "=== ML Collector Service Status ==="
echo
systemctl --user status "${SERVICE_NAME}" --no-pager || true

echo
echo "=== Recent Logs (last 20 lines) ==="
echo
journalctl --user -u "${SERVICE_NAME}" -n 20 --no-pager || true

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
