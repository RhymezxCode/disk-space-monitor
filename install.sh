#!/usr/bin/env bash
#
# Installs the Disk Space Monitor as a desktop app for the current user.
# - ensures the psutil dependency is available
# - creates a launcher in the GNOME/KDE app grid
#
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/disk-space-monitor.desktop"

echo "==> Checking psutil..."
if python3 -c "import psutil" 2>/dev/null; then
    echo "    psutil already installed."
else
    echo "    Installing psutil..."
    # Try a normal user install; fall back to a venv-friendly flag if PEP 668 blocks it.
    pip3 install --user psutil 2>/dev/null \
        || pip3 install --user --break-system-packages psutil \
        || { echo "    Could not auto-install. Run: sudo apt install python3-psutil"; }
fi

echo "==> Creating launcher at $DESKTOP_FILE ..."
mkdir -p "$APPS_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Disk Space Monitor
Comment=Floating always-on-top disk usage widget
Exec=python3 $DIR/disk_monitor.py
Icon=drive-harddisk
Terminal=false
Categories=System;Monitor;Utility;
StartupNotify=false
EOF
chmod +x "$DESKTOP_FILE" "$DIR/disk_monitor.py" "$DIR/run.sh" 2>/dev/null || true

echo "==> Done."
echo "    Launch it from your app grid ('Disk Space Monitor'),"
echo "    or run directly:  $DIR/run.sh"
