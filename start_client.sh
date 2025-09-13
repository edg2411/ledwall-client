#!/bin/bash
# Start script for LED Wall client on Linux/Raspberry Pi
# Supports both direct display and headless operation

echo "Starting LED Wall Client..."

# Activate virtual environment
source venv/bin/activate

# Check if venv is activated properly
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: Virtual environment not activated. Try running setup_client.sh first."
    exit 1
fi

# Check display situation
if [ -n "$SSH_CONNECTION" ]; then
    echo "Detected SSH session"
    
    # If DISPLAY is already set to the Pi's display, use that
    if [ -n "$DISPLAY" ] && [[ "$DISPLAY" == ":0" || "$DISPLAY" == ":0.0" ]]; then
        echo "Using Pi's physical display at $DISPLAY"
    else
        # Check if a physical display is available on the Pi (display :0)
        if DISPLAY=:0 xset q &>/dev/null; then
            echo "Physical display detected on the Pi, redirecting to :0"
            export DISPLAY=:0
        else
            echo "No physical display detected, starting with virtual display"
            
            # Check if Xvfb is installed
            if ! command -v Xvfb &> /dev/null; then
                echo "Xvfb not found! Please install it with: sudo apt-get install xvfb"
                echo "Then run this script again."
                exit 1
            fi
            
            # Kill any existing Xvfb instances
            pkill Xvfb || true
            
            # Start Xvfb
            Xvfb :1 -screen 0 1024x768x16 &
            export DISPLAY=:1
            
            echo "Virtual display started on $DISPLAY"
            
            # Wait for Xvfb to initialize
            sleep 2
        fi
    fi
fi

echo "Using display: $DISPLAY"

# Run the client using the new main.py entry point
python main.py

# If we started Xvfb, clean it up
if [ -n "$SSH_CONNECTION" ] && [ "$DISPLAY" = ":1" ]; then
    echo "Stopping virtual display"
    pkill Xvfb
fi

# Keep the terminal open if the client exits with an error
if [ $? -ne 0 ]; then
    echo
    echo "Client exited with an error. Press any key to close this window..."
    read -n 1
fi

# Deactivate virtual environment
deactivate