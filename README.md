# LED Wall Client

This client supports both **video playback** and **dynamic price display** for LED wall systems.

## Installation Instructions

1. Unzip this package:
   ```
   unzip ledwall_client.zip -d ledwall_client
   cd ledwall_client
   ```

2. Run the setup script:
   ```
   chmod +x setup_client.sh
   ./setup_client.sh
   ```

3. Start the client:
    ```
    ./start_client.sh
    ```

### Windows Setup
```powershell
# Install dependencies
pip install -r requirements.txt

# Run client
python main.py
```

## System Requirements

### Hardware Support
- **Raspberry Pi** (any model) - Original target
- **Windows PC** (10/11) - Full support added
- **Linux systems** - Compatible

### Software Requirements
- **Python 3.7 or newer**
- **FFmpeg** (for media playback and price display)
- **PIL/Pillow** (for price image generation)
- **xdotool** (for window management on Linux/Raspberry Pi)

### Display Features
- **Video Playback**: MP4, AVI, and other FFmpeg-supported formats
- **Price Display**: Dynamic text rendering with LED-optimized colors
- **Real-time Updates**: WebSocket synchronization with server
- **Dual Mode**: Seamless switching between video and price display

## Running as a Service

To install the client as a system service that starts automatically on boot:

```
sudo ./setup_service.sh
```

This will create and enable a systemd service.

## Price Display Configuration

### Display Settings
- **Resolution**: Configurable in `config.json` (default: 256×320)
- **Layout**: 5 rows with left/right price duplication
- **Colors**: LED-optimized high-contrast colors
- **Fonts**: Auto-scaling for optimal readability

### Server Connection
Update `config.json` to connect to your server:
```json
{
  "server_url": "http://YOUR_SERVER_IP:5050",
  "width": 256,
  "height": 320,
  "name": "your_client_name"
}
```

### Price Display Features
- **Real-time Updates**: Automatic synchronization with server
- **Visual Generation**: PIL-based image creation
- **FFmpeg Integration**: Uses existing video pipeline
- **Dual Mode**: Switch between video and price display

## Troubleshooting

### General Issues
1. Check the `client.log` file for error messages
2. Ensure FFmpeg is installed and in PATH
3. Verify server connection in `config.json`
4. Check Python version (3.7+ required)

### Video Playback Issues
- Ensure FFmpeg supports your video format
- Check file permissions in `downloads/` folder
- Verify video file integrity

### Price Display Issues
- Ensure PIL/Pillow is installed: `pip install pillow`
- Check server connection for price updates
- Verify display resolution settings
- Confirm FFmpeg can display images

### Windows-Specific Issues
- Use PowerShell for API calls (not curl)
- Ensure FFmpeg is added to system PATH
- Check Windows Firewall settings for port 5050

### Raspberry Pi Issues
- Install xdotool: `sudo apt-get install xdotool`
- Check display permissions
- Verify FFmpeg installation

### Connection Issues
- Confirm server is running on correct IP/port
- Check network connectivity between devices
- Verify WebSocket connection in logs
