#!/usr/bin/env bash
#
# Uninstalls the Disk Space Monitor desktop integration for the current user.
# - removes the app launcher (created by install.sh)
# - removes the autostart entry (created by "Start on login" in Settings)
# - removes saved settings
#
# It deliberately leaves the program files in this folder untouched — delete the
# folder by hand if you also want to remove the code.
#
set -euo pipefail

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/disk-space-monitor"

LAUNCHER="$APPS_DIR/disk-space-monitor.desktop"
AUTOSTART="$AUTOSTART_DIR/disk-space-monitor.desktop"

echo "==> Removing app launcher..."
rm -f "$LAUNCHER" && echo "    removed $LAUNCHER" || true

echo "==> Removing autostart entry..."
rm -f "$AUTOSTART" && echo "    removed $AUTOSTART" || true

echo "==> Removing saved settings..."
rm -rf "$CONFIG_DIR" && echo "    removed $CONFIG_DIR" || true

echo "==> Done."
echo "    The program files in $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "    were left in place — delete that folder if you want to remove the code."
echo "    System packages (python3-tk, python3-psutil) were left installed."
