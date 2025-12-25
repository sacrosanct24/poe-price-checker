#!/bin/bash
# Stop ML collector service

SERVICE_NAME="poe-ml-collector"

echo "Stopping ML collector service..."
systemctl --user stop "${SERVICE_NAME}"

echo
echo "Service status:"
systemctl --user status "${SERVICE_NAME}" --no-pager || true

echo
echo "To restart: systemctl --user start ${SERVICE_NAME}"
echo "To disable: systemctl --user disable ${SERVICE_NAME}"
