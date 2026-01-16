#!/bin/bash
# Install a daily ML feasibility report job (systemd user timer or cron fallback).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="poe-ml-feasibility"

install_systemd() {
  mkdir -p "${UNIT_DIR}"

  cat > "${UNIT_DIR}/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=PoE ML feasibility daily report

[Service]
Type=oneshot
WorkingDirectory=${REPO_DIR}
ExecStart=${REPO_DIR}/.venv/bin/python ${REPO_DIR}/scripts/ml-feasibility-daily.py
EOF

  cat > "${UNIT_DIR}/${SERVICE_NAME}.timer" <<EOF
[Unit]
Description=Run PoE ML feasibility report daily at noon

[Timer]
OnCalendar=*-*-* 12:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}.timer"
  echo "Installed systemd user timer: ${SERVICE_NAME}.timer"
}

install_cron() {
  local cron_line
  cron_line="0 12 * * * ${REPO_DIR}/.venv/bin/python ${REPO_DIR}/scripts/ml-feasibility-daily.py"
  (crontab -l 2>/dev/null | grep -v "ml-feasibility-daily.py" || true; echo "${cron_line}") | crontab -
  echo "Installed crontab entry: ${cron_line}"
}

if systemctl --user list-units >/dev/null 2>&1; then
  install_systemd
else
  echo "systemd --user unavailable; falling back to cron."
  install_cron
fi
