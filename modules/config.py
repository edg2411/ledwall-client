"""
Configuration Manager for LED Wall Client
Handles loading, saving, and accessing configuration values.
"""
import os
import json
import socket
import logging
import platform

logger = logging.getLogger("led_client.config")

class ConfigManager:
    """Manages client configuration settings"""
    
    # Default configuration values
    DEFAULT_SERVER_URL = "http://localhost:5000"
    DEFAULT_WIDTH = 256
    DEFAULT_HEIGHT = 160
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        """Initialize configuration manager"""
        self.is_windows = platform.system() == "Windows"
        self.is_raspberry_pi = self._detect_raspberry_pi()
        self.config = self.load()
        
        # Ensure critical settings are present
        self._ensure_defaults()
    
    def _detect_raspberry_pi(self):
        """Detect if running on a Raspberry Pi"""
        try:
            return os.path.exists('/sys/firmware/devicetree/base/model') and 'raspberry pi' in open('/sys/firmware/devicetree/base/model', 'r').read().lower()
        except:
            return False
    
    def _ensure_defaults(self):
        """Ensure all required configuration values are present"""
        if 'width' not in self.config:
            self.config['width'] = self.DEFAULT_WIDTH
        if 'height' not in self.config:
            self.config['height'] = self.DEFAULT_HEIGHT
        if 'server_url' not in self.config:
            self.config['server_url'] = self.DEFAULT_SERVER_URL
        if 'name' not in self.config:
            hostname = socket.gethostname()
            prefix = "RaspberryPi-" if self.is_raspberry_pi else ""
            self.config['name'] = f"{prefix}{hostname}"
        
        # Always set the resolution to the fixed value
        self.config['width'] = self.DEFAULT_WIDTH
        self.config['height'] = self.DEFAULT_HEIGHT
        
        # Save changes
        self.save()
    
    def load(self):
        """Load configuration from file"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {str(e)}")
        
        return {}
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def get(self, key, default=None):
        """Get a configuration value with optional default"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value and save"""
        self.config[key] = value
        self.save()
    
    def get_client_id(self):
        """Get the client ID or None if not registered"""
        return self.config.get('client_id')
    
    def set_client_id(self, client_id):
        """Set the client ID after registration"""
        self.config['client_id'] = client_id
        self.save()
    
    @property
    def server_url(self):
        """Get the server URL"""
        return self.config.get('server_url', self.DEFAULT_SERVER_URL)
    
    @property
    def width(self):
        """Get screen width"""
        return self.config.get('width', self.DEFAULT_WIDTH)
    
    @property
    def height(self):
        """Get screen height"""
        return self.config.get('height', self.DEFAULT_HEIGHT)
    
    @property
    def name(self):
        """Get client name"""
        return self.config.get('name', socket.gethostname())