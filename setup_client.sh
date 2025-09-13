#!/bin/bash
# Setup script for LED Wall client on Linux/Raspberry Pi

echo "Setting up LED Wall Client..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3 with: sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        echo "Try installing venv with: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for FFmpeg
echo "Checking for FFmpeg..."
if ! command -v ffplay &> /dev/null; then
    echo "WARNING: FFmpeg/ffplay not found!"
    echo "Would you like to install FFmpeg now? (y/n)"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "Installing FFmpeg..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y ffmpeg
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        else
            echo "Could not determine package manager. Please install FFmpeg manually."
            echo "For Debian/Ubuntu/Raspberry Pi: sudo apt install ffmpeg"
            echo "For Fedora: sudo dnf install ffmpeg"
            echo "For CentOS/RHEL: sudo yum install ffmpeg"
        fi
    else
        echo "Please install FFmpeg manually to play media content."
    fi
fi

# Install xdotool for window management
echo "Checking for xdotool (needed for window management)..."
if ! command -v xdotool &> /dev/null; then
    echo "Would you like to install xdotool for window positioning? (y/n)"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "Installing xdotool..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y xdotool
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y xdotool
        elif command -v yum &> /dev/null; then
            sudo yum install -y xdotool
        else
            echo "Could not determine package manager. Please install xdotool manually."
            echo "For Debian/Ubuntu/Raspberry Pi: sudo apt install xdotool"
        fi
    fi
fi

# Ensure download directory exists
echo "Creating downloads directory..."
mkdir -p downloads

# Configure server URL
echo
echo "Configuration:"
echo "--------------"
echo "Please enter the server URL (default: http://localhost:5000):"
read -r server_url
server_url=${server_url:-http://localhost:5000}

echo "Please enter a name for this screen (default: $(hostname)):"
read -r screen_name
screen_name=${screen_name:-$(hostname)}

# Create or update config.json
echo "Creating configuration file..."
cat > config.json << EOL
{
    "server_url": "$server_url",
    "name": "$screen_name",
    "width": 180,
    "height": 180
}
EOL

echo
echo "Setup complete!"
echo "Run ./start_client.sh to start the LED Wall client."

# Deactivate virtual environment
deactivate