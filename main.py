#!/usr/bin/env python3
"""
LED Wall Client - Main Entry Point
This is the main entry point for the LED Wall Client application.
"""
import os
import sys
import signal
import logging
import time
from modules.config import ConfigManager
from modules.player import MediaPlayer
from modules.network import ServerConnection
from modules.ui import UIManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("client.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("led_client")

class LEDWallClient:
    """Main LED Wall Client application class"""
    
    # Static instance for global access
    instance = None
    
    def __init__(self):
        """Initialize the LED Wall Client"""
        self.running = True
        
        # Set static instance for global access
        LEDWallClient.instance = self
        
        # Handle exit signals
        signal.signal(signal.SIGINT, self.handle_exit_signal)
        signal.signal(signal.SIGTERM, self.handle_exit_signal)
        
        # Initialize components
        logger.info("Initializing LED Wall Client...")
        self.config = ConfigManager()
        self.player = MediaPlayer(self.config)
        self.ui = UIManager(self.player)
        self.server = ServerConnection(
            self.config, 
            content_callback=self.handle_content_update
        )
        
        # Set current content tracking
        self.current_content = None
        
        # Check for FFplay
        if not self.player.is_ffplay_available():
            logger.warning("FFplay not found! You need to install FFmpeg to play media content.")
            if self.player.is_windows:
                logger.warning("Please visit https://ffmpeg.org/download.html to download FFmpeg and add it to your system PATH.")
                logger.warning("Alternatively, you can download from https://github.com/BtbN/FFmpeg-Builds/releases")
            else:
                logger.warning("On Raspberry Pi, install with: sudo apt-get install ffmpeg")
            logger.warning("After installing, restart this application.")
    
    def handle_exit_signal(self, signum, frame):
        """Handle exit signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def handle_content_update(self, content_id, content_info):
        """Handle content updates from the server
        
        Args:
            content_id: ID of the content
            content_info: Dict containing content info
            
        Returns:
            bool: True if content was played successfully
        """
        logger.info(f"Content update received: {content_id}")
        
        # Skip if already playing this content
        if content_id == self.current_content:
            logger.info(f"Already playing content {content_id}")
            return True
        
        # Stop current playback
        self.player.stop()
        
        # Start playing the new content
        file_path = os.path.join("downloads", content_info['filename'])
        if not os.path.exists(file_path):
            logger.error(f"Content file does not exist: {file_path}")
            return False
            
        success = self.player.play(
            file_path, 
            content_info, 
            callback=self.handle_playback_ended
        )
        
        if success:
            # Update current content
            self.current_content = content_id
            # Send status update to server
            self.server.send_status_update('playing', content_id)
            return True
        else:
            logger.error(f"Failed to play content: {content_id}")
            # Send error status to server
            self.server.send_status_update('error', content_id, 'Failed to play content')
            return False
    
    def handle_playback_ended(self, content_info, exit_code):
        """Handle playback end event
        
        Args:
            content_info: Dict containing content info
            exit_code: Exit code from the player
        """
        content_id = content_info['id']
        
        # Only handle if still current content
        if content_id != self.current_content:
            logger.info(f"Playback ended for old content {content_id}, ignoring")
            return
            
        if exit_code != 0:
            logger.warning(f"Playback ended unexpectedly with code {exit_code}")
            # Restart with delay to prevent rapid restart loops
            time.sleep(2)
            
            # Try to restart playback
            file_path = os.path.join("downloads", content_info['filename'])
            if os.path.exists(file_path):
                logger.info(f"Restarting playback of {content_id}")
                self.player.play(
                    file_path,
                    content_info,
                    callback=self.handle_playback_ended
                )
            else:
                logger.error(f"Content file no longer exists: {file_path}")
                # Clear current content so it can be reassigned
                self.current_content = None
        else:
            logger.info(f"Playback ended normally for {content_id}")
            # Send stopped status to server
            self.server.send_status_update('stopped', content_id)
            # Clear current content
            self.current_content = None
    
    def cleanup(self):
        """Clean up resources before exit"""
        logger.info("Cleaning up resources...")
        if hasattr(self, 'player'):
            self.player.stop()
        if hasattr(self, 'server'):
            self.server.disconnect()
        logger.info("Cleanup complete")
    
    def run(self):
        """Main application loop"""
        logger.info("Starting LED Wall Client")
        
        # Register with server if needed
        if not self.config.get_client_id():
            if not self.server.register():
                logger.error("Failed to register with server. Exiting.")
                return
        
        # Connect to server
        if not self.server.connect():
            logger.warning("Could not connect to server via WebSocket, falling back to polling")
        
        try:
            # Main loop
            while self.running:
                if not self.server.is_connected():
                    self.server.reconnect()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Client stopped by user")
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    client = LEDWallClient()
    client.run()

if __name__ == "__main__":
    main()