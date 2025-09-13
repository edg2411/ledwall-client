"""
UI Manager Module for LED Wall Client
Handles window interactions and hotkeys
"""
import os
import logging
import platform
import subprocess
import threading

logger = logging.getLogger("led_client.ui")

class UIManager:
    """Manages UI interactions like hotkeys and window visibility"""
    
    def __init__(self, media_player):
        """Initialize the UI manager
        
        Args:
            media_player: MediaPlayer instance to control
        """
        self.player = media_player
        self.is_windows = platform.system() == "Windows"
        self.is_raspberry_pi = self.player.is_raspberry_pi
        self.player_hidden = False
        self._setup_hotkeys()
    
    def _setup_hotkeys(self):
        """Set up hotkeys based on platform"""
        if self.is_windows:
            try:
                # Only import keyboard on Windows
                import keyboard
                keyboard.add_hotkey('ctrl+h', self.toggle_visibility)
                logger.info("Registered Ctrl+H hotkey to toggle player visibility")
            except ImportError:
                logger.warning("Keyboard module not available. Hotkey functionality disabled.")
            except Exception as e:
                logger.error(f"Failed to register hotkey: {str(e)}")
        else:
            # For Linux/RPi we could set up other hotkey mechanisms here
            if self.is_raspberry_pi and 'DISPLAY' in os.environ:
                logger.info("Running on Raspberry Pi with X11, hotkeys not automatically configured")
                # Could use xbindkeys or similar for RPi
    
    def toggle_visibility(self):
        """Toggle player window visibility"""
        self.player_hidden = not self.player_hidden
        logger.info(f"Player visibility toggled: {'hidden' if self.player_hidden else 'visible'}")
        
        if self.player_hidden:
            self.hide_player()
        else:
            self.show_player()
    
    def hide_player(self):
        """Hide the player window"""
        self.player.hide()
    
    def show_player(self):
        """Show the player window"""
        self.player.show()