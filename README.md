# LED Wall Client

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

## System Requirements

- Raspberry Pi (any model)
- Raspbian/Raspberry Pi OS
- Python 3.7 or newer
- FFmpeg (for media playback)
- xdotool (for window management)

## Running as a Service

To install the client as a system service that starts automatically on boot:

```
sudo ./setup_service.sh
```

This will create and enable a systemd service.

## Troubleshooting

If you encounter issues:
1. Check the client.log file for error messages
2. Ensure FFmpeg is installed
3. For window positioning issues, make sure xdotool is installed
