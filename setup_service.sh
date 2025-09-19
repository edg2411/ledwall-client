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

# Get the user's home directory and X authority
USER_HOME=$(eval echo ~$SERVICE_USER)
USER_XAUTHORITY="$USER_HOME/.Xauthority"

echo "User home: $USER_HOME"
echo "X authority file: $USER_XAUTHORITY"

# Check if virtual environment exists
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "ERROR: Virtual environment not found at ${SCRIPT_DIR}/venv"
    echo "Please run setup_client.sh first to create the virtual environment."
    exit 1
fi

# Detect display configuration (run as the actual user)
HAS_PHYSICAL_DISPLAY=false
echo "Checking display access for user $SERVICE_USER..."

# Try to detect available displays
if sudo -u "$SERVICE_USER" DISPLAY=:0 xset q &>/dev/null 2>&1; then
    echo "Physical display detected on :0"
    HAS_PHYSICAL_DISPLAY=true
    DETECTED_DISPLAY=":0"
elif sudo -u "$SERVICE_USER" DISPLAY=:1 xset q &>/dev/null 2>&1; then
    echo "Virtual display detected on :1"
    HAS_PHYSICAL_DISPLAY=true
    DETECTED_DISPLAY=":1"
else
    echo "No accessible display found for user $SERVICE_USER"
    echo "Make sure the user is logged in and has an active X session"
    echo "You can also try running: sudo -u $SERVICE_USER xhost +"
fi

# If using physical display, ask if the user wants to use it
USE_PHYSICAL_DISPLAY=false
if [ "$HAS_PHYSICAL_DISPLAY" = true ]; then
    read -p "Display detected on $DETECTED_DISPLAY. Would you like to use it for the LED Wall? (y/n): " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        USE_PHYSICAL_DISPLAY=true
    fi
else
    echo "No display detected. The service will be configured to use virtual display with Xvfb."
    echo "Note: Virtual display may not show content on screen, only for headless operation."
fi

# Create display check script
cat > /usr/local/bin/wait-for-display.sh << 'EOL'
#!/bin/bash
# Script to wait for display to be available

DISPLAY_TO_CHECK="${1:-:0}"
MAX_WAIT=30
WAIT_COUNT=0

echo "Waiting for display $DISPLAY_TO_CHECK to be available..."

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if DISPLAY="$DISPLAY_TO_CHECK" xset q >/dev/null 2>&1; then
        echo "Display $DISPLAY_TO_CHECK is now available!"
        exit 0
    fi
    
    echo "Display $DISPLAY_TO_CHECK not ready yet, waiting... ($WAIT_COUNT/$MAX_WAIT)"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

echo "Display $DISPLAY_TO_CHECK not available after $MAX_WAIT seconds"
exit 1
EOL

chmod +x /usr/local/bin/wait-for-display.sh

# Create appropriate systemd service file based on display choice
if [ "$USE_PHYSICAL_DISPLAY" = true ]; then
    echo "Configuring service to use physical display at $DETECTED_DISPLAY"
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
Environment="DISPLAY=${DETECTED_DISPLAY}"
Environment="HOME=${USER_HOME}"
Environment="XAUTHORITY=${USER_XAUTHORITY}"
Environment="PATH=${SCRIPT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStartPre=/usr/local/bin/wait-for-display.sh ${DETECTED_DISPLAY}
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
Environment="HOME=${USER_HOME}"
Environment="XAUTHORITY=${USER_XAUTHORITY}"
Environment="PATH=${SCRIPT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStartPre=/bin/sleep 5
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

# Try to set up display permissions for the user
echo "Setting up display permissions..."
if [ "$USE_PHYSICAL_DISPLAY" = true ]; then
    echo "Attempting to grant display access to user $SERVICE_USER..."
    sudo -u "$SERVICE_USER" xhost + &>/dev/null || true
fi

# Ask if user wants to create a delayed startup timer as backup
read -p "Do you want to create a delayed startup timer as backup? (y/n): " create_timer
if [[ "$create_timer" =~ ^[Yy]$ ]]; then
    echo "Creating delayed startup timer..."

    # Create timer service
    cat > /etc/systemd/system/ledwall.timer << EOL
[Unit]
Description=LED Wall Client Delayed Startup Timer
Requires=ledwall.service

[Timer]
OnBootSec=30s
Unit=ledwall.service

[Install]
WantedBy=timers.target
EOL

    # Disable the automatic startup and enable timer instead
    systemctl disable ledwall.service
    systemctl enable ledwall.timer
    systemctl start ledwall.timer

    echo "Timer created! Service will start 30 seconds after boot."
fi

if systemctl start ledwall.service; then
    echo "LED Wall service started successfully"
else
    echo "ERROR: Failed to start LED Wall service"
    echo "Check the service status with: sudo systemctl status ledwall"
    echo "Check logs with: sudo journalctl -u ledwall -f"
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
if [[ "$create_timer" =~ ^[Yy]$ ]]; then
    echo "Timer management:"
    echo "  sudo systemctl start ledwall.timer    # Start timer"
    echo "  sudo systemctl stop ledwall.timer     # Stop timer"
    echo "  sudo systemctl status ledwall.timer   # Check timer status"
    echo
fi
echo "View logs with:"
echo "  sudo journalctl -u ledwall -f"
echo
echo "IMPORTANT: If the service fails to display content at boot, you may need to:"
echo "1. Ensure the user $SERVICE_USER is logged in with an active X session"
echo "2. Allow the user to access the display:"
echo "   sudo -u $SERVICE_USER xhost +"
echo "3. Or add the service user to the 'video' group:"
echo "   sudo usermod -a -G video $SERVICE_USER"
echo
echo "ALTERNATIVE: If boot startup still fails, you can create a delayed startup:"
echo "  sudo systemctl disable ledwall"
echo "  sudo systemctl enable ledwall.timer  # (if you want to create a timer)"
echo
echo "Or start manually after login:"
echo "  sudo systemctl start ledwall"
echo
echo "If using virtual display (Xvfb), content will run headless and won't be visible on screen."

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
if [[ "$create_timer" =~ ^[Yy]$ ]]; then
    echo "  sudo systemctl disable ledwall.timer"
    echo "  sudo systemctl stop ledwall.timer"
else
    echo "  sudo systemctl disable ledwall"
fi
if [ "$USE_PHYSICAL_DISPLAY" = false ]; then
    echo "  sudo systemctl disable xvfb-ledwall"
fi