#!/bin/bash
# Setup ML collector as a systemd user service
# Run this script once to install and start the service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="poe-ml-collector"
SERVICE_FILE="${SCRIPT_DIR}/ml-collector.service"
USER_SERVICE_DIR="${HOME}/.config/systemd/user"

echo "=== Setting up ML Collector Service ==="
echo

# Create user service directory if needed
mkdir -p "${USER_SERVICE_DIR}"

# Copy service file
echo "Copying service file to ${USER_SERVICE_DIR}/${SERVICE_NAME}.service"
cp "${SERVICE_FILE}" "${USER_SERVICE_DIR}/${SERVICE_NAME}.service"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable service (start on login)
echo "Enabling service..."
systemctl --user enable "${SERVICE_NAME}"

# Start service
echo "Starting service..."
systemctl --user start "${SERVICE_NAME}"

# Enable lingering (keeps user services running after logout)
echo "Enabling linger for user ${USER}..."
loginctl enable-linger "${USER}"

echo
echo "=== Setup Complete ==="
echo
echo "Service status:"
systemctl --user status "${SERVICE_NAME}" --no-pager || true

echo
echo "To check logs:  journalctl --user -u ${SERVICE_NAME} -f"
echo "To stop:        systemctl --user stop ${SERVICE_NAME}"
echo "To restart:     systemctl --user restart ${SERVICE_NAME}"
