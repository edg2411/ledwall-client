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

# Get the actual user who invoked sudo (not root)
if [ -n "$SUDO_USER" ]; then
    SERVICE_USER="$SUDO_USER"
    SERVICE_GROUP="$(id -gn "$SUDO_USER")"
else
    SERVICE_USER="$(logname)"
    SERVICE_GROUP="$(logname)"
fi

echo "Service will run as user: $SERVICE_USER"

# Check if virtual environment exists
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "ERROR: Virtual environment not found at ${SCRIPT_DIR}/venv"
    echo "Please run setup_client.sh first to create the virtual environment."
    exit 1
fi

# Detect display configuration (run as the actual user)
HAS_PHYSICAL_DISPLAY=false
if sudo -u "$SERVICE_USER" DISPLAY=:0 xset q &>/dev/null; then
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
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${SCRIPT_DIR}
Environment="DISPLAY=:0"
Environment="PATH=${SCRIPT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOL
else
    echo "Configuring service to use virtual display with Xvfb"

    # Create Xvfb service first
    cat > /etc/systemd/system/xvfb-ledwall.service << EOL
[Unit]
Description=Xvfb for LED Wall Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
ExecStart=/usr/bin/Xvfb :1 -screen 0 1024x768x16 -ac
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

    # Create main service
    cat > /etc/systemd/system/ledwall.service << EOL
[Unit]
Description=LED Wall Client
After=network-online.target xvfb-ledwall.service
Wants=network-online.target xvfb-ledwall.service
Requires=xvfb-ledwall.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${SCRIPT_DIR}
Environment="DISPLAY=:1"
Environment="PATH=${SCRIPT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

    # Enable Xvfb service
    systemctl enable xvfb-ledwall.service
fi

# Set proper permissions
chmod 644 /etc/systemd/system/ledwall.service

# Reload systemd, enable and start the service
echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling service..."
if [ "$USE_PHYSICAL_DISPLAY" = false ]; then
    echo "Enabling Xvfb service..."
    systemctl enable xvfb-ledwall.service
fi

if systemctl enable ledwall.service; then
    echo "LED Wall service enabled successfully"
else
    echo "ERROR: Failed to enable LED Wall service"
    exit 1
fi

echo "Starting service..."
if [ "$USE_PHYSICAL_DISPLAY" = false ]; then
    echo "Starting Xvfb service..."
    systemctl start xvfb-ledwall.service
fi

if systemctl start ledwall.service; then
    echo "LED Wall service started successfully"
else
    echo "ERROR: Failed to start LED Wall service"
    echo "Check the service status with: sudo systemctl status ledwall"
    exit 1
fi

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet ledwall.service; then
    echo "✓ Service is running successfully!"
else
    echo "⚠ Service may have issues. Check status with: sudo systemctl status ledwall"
fi

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

if [ "$USE_PHYSICAL_DISPLAY" = false ]; then
    echo
    echo "Xvfb service commands:"
    echo "  sudo systemctl start xvfb-ledwall    # Start Xvfb"
    echo "  sudo systemctl stop xvfb-ledwall     # Stop Xvfb"
    echo "  sudo systemctl status xvfb-ledwall   # Check Xvfb status"
    echo "  sudo journalctl -u xvfb-ledwall -f   # View Xvfb logs"
fi

echo
echo "To disable auto-startup:"
echo "  sudo systemctl disable ledwall"
if [ "$USE_PHYSICAL_DISPLAY" = false ]; then
    echo "  sudo systemctl disable xvfb-ledwall"
fi