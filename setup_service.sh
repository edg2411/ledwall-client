#!/bin/bash
# Setup LED Wall client as a systemd service

echo "Setting up LED Wall Client as a system service..."
echo "This will allow the client to run automatically at boot."
echo

# Must run as root/sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (sudo)"
    echo "Please run with: sudo ./setup_service.sh"
    exit 1
fi

# Check for Xvfb (needed as fallback if physical display fails)
if ! command -v Xvfb &> /dev/null; then
    echo "Installing Xvfb for virtual display support..."
    apt-get update
    apt-get install -y xvfb
fi

# Get the current directory (absolute path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect display configuration
HAS_PHYSICAL_DISPLAY=false
if DISPLAY=:0 xset q &>/dev/null; then
    echo "Physical display detected on :0"
    HAS_PHYSICAL_DISPLAY=true
fi

# If using physical display, ask if the user wants to use it
USE_PHYSICAL_DISPLAY=false
if [ "$HAS_PHYSICAL_DISPLAY" = true ]; then
    read -p "Physical display detected. Would you like to use it for the LED Wall? (y/n): " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        USE_PHYSICAL_DISPLAY=true
    fi
fi

# Create appropriate systemd service file based on display choice
if [ "$USE_PHYSICAL_DISPLAY" = true ]; then
    echo "Configuring service to use physical display at :0"
    cat > /etc/systemd/system/ledwall.service << EOL
[Unit]
Description=LED Wall Client
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=$(logname)
Group=$(logname)
WorkingDirectory=${SCRIPT_DIR}
Environment="DISPLAY=:0"
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/client.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOL
else
    echo "Configuring service to use virtual display with Xvfb"
    cat > /etc/systemd/system/ledwall.service << EOL
[Unit]
Description=LED Wall Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(logname)
Group=$(logname)
WorkingDirectory=${SCRIPT_DIR}
Environment="DISPLAY=:1"
ExecStartPre=/usr/bin/Xvfb :1 -screen 0 1024x768x16 -ac
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/client.py
ExecStopPost=/usr/bin/pkill Xvfb
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL
fi

# Set proper permissions
chmod 644 /etc/systemd/system/ledwall.service

# Reload systemd, enable and start the service
systemctl daemon-reload
systemctl enable ledwall.service
systemctl start ledwall.service

echo
echo "Service installed and started!"
echo
echo "You can manage the service with these commands:"
echo "  sudo systemctl start ledwall    # Start the service"
echo "  sudo systemctl stop ledwall     # Stop the service"
echo "  sudo systemctl restart ledwall  # Restart the service"
echo "  sudo systemctl status ledwall   # Check service status"
echo
echo "View logs with:"
echo "  sudo journalctl -u ledwall -f"