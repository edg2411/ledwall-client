"""
Network Module for LED Wall Client
Handles communication with the server via HTTP and WebSocket
"""
import os
import time
import json
import logging
import requests
import threading

logger = logging.getLogger("led_client.network")

# Default constants
DOWNLOAD_FOLDER = "downloads"
POLLING_INTERVAL = 30  # seconds

class ServerConnection:
    """Handles communication with the LED Wall server"""
    
    def __init__(self, config_manager, content_callback=None):
        """Initialize server connection
        
        Args:
            config_manager: Configuration manager instance
            content_callback: Callback function for content updates
        """
        self.config = config_manager
        self.content_callback = content_callback
        self.server_url = self.config.server_url
        self.client_id = self.config.get_client_id()
        self.socket = None
        self.socket_connected = False
        self._polling_thread = None
        self._polling_active = False
        self._last_handled_content_id = None
        
        # Ensure download directory exists
        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    
    def register(self):
        """Register this client with the server
        
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/register",
                json={
                    'name': self.config.name,
                    'width': self.config.width,
                    'height': self.config.height
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.client_id = data.get('client_id')
                self.config.set_client_id(self.client_id)
                logger.info(f"Successfully registered with server. Client ID: {self.client_id}")
                return True
            else:
                logger.error(f"Failed to register with server: {response.text}")
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
        
        return False
    
    def connect(self):
        """Connect to the server via WebSocket
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Try to import socketio - if not available, we'll fall back to polling
            import socketio
            
            # Initialize socket.io client
            self.socket = socketio.Client()
            self._setup_socket_handlers()
            
            # Connect to server
            self.socket.connect(self.server_url)
            return True
        except ImportError:
            logger.warning("python-socketio not available, using HTTP polling only")
            # Start polling thread as fallback
            self._start_polling()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to server: {str(e)}")
            # Start polling thread as fallback
            self._start_polling()
            return False
    
    def reconnect(self):
        """Attempt to reconnect to the server if disconnected"""
        if self.socket:
            try:
                if not self.socket_connected:
                    logger.info("Attempting to reconnect to server...")
                    self.socket.connect(self.server_url)
                    return True
            except Exception as e:
                logger.error(f"Failed to reconnect: {str(e)}")
                # Fall back to polling if reconnection fails
                if not self._polling_active:
                    self._start_polling()
        elif not self._polling_active:
            # No socket, make sure polling is active
            self._start_polling()
        
        return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket and self.socket_connected:
            try:
                self.socket.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from server: {str(e)}")
        
        # Stop polling if active
        self._polling_active = False
    
    def is_connected(self):
        """Check if connected to the server via WebSocket
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.socket_connected
    
    def _setup_socket_handlers(self):
        """Set up socket.io event handlers"""
        if not self.socket:
            return
            
        @self.socket.event
        def connect():
            logger.info("Connected to server")
            self.socket_connected = True
            # Register with socket after connection
            self.socket.emit('register', {'client_id': self.client_id})
            
            # Stop polling if active (no need for both)
            self._polling_active = False
        
        @self.socket.event
        def connect_error(data):
            logger.error(f"Connection error: {data}")
            self.socket_connected = False
            
            # Start polling as fallback if not already active
            if not self._polling_active:
                self._start_polling()
        
        @self.socket.event
        def disconnect():
            logger.info("Disconnected from server")
            self.socket_connected = False
            
            # Start polling as fallback if not already active
            if not self._polling_active:
                self._start_polling()
        
        @self.socket.on('registration_success')
        def on_registration_success(data):
            logger.info(f"Socket registration successful: {data}")
        
        @self.socket.on('registration_failed')
        def on_registration_failed(data):
            logger.error(f"Socket registration failed: {data}")
        
        @self.socket.on('content_assigned')
        def on_content_assigned(data):
            content_id = data.get('content_id')
            logger.info(f"New content assigned via WebSocket: {content_id}")
            self._handle_content_update(content_id)
    
    def _start_polling(self):
        """Start polling thread for server updates"""
        if self._polling_active:
            return
            
        self._polling_active = True
        self._polling_thread = threading.Thread(target=self._polling_loop)
        self._polling_thread.daemon = True
        self._polling_thread.start()
        logger.info("Started polling for server updates")
    
    def _polling_loop(self):
        """Main polling loop to check for content updates"""
        while self._polling_active:
            try:
                self.check_for_updates()
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
            
            # Sleep before next poll
            time.sleep(POLLING_INTERVAL)
    
    def check_for_updates(self):
        """Check for content updates from server using HTTP"""
        try:
            if not self.client_id:
                logger.warning("No client ID available, skipping update check")
                return False
                
            # Get client info from server
            response = requests.get(f"{self.server_url}/api/client/{self.client_id}")
            if response.status_code == 200:
                client_info = response.json()
                assigned_content = client_info.get('current_content')
                
                # If new content is assigned, handle it
                if assigned_content and assigned_content != self._last_handled_content_id:
                    logger.info(f"New content detected via polling: {assigned_content}")
                    self._handle_content_update(assigned_content)
                    return True
            else:
                logger.error(f"Failed to get client info: {response.status_code}")
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
        
        return False
    
    def _handle_content_update(self, content_id):
        """Handle content update from server
        
        Args:
            content_id: ID of the content to handle
        """
        try:
            # Prevent duplicate handling of the same content assignment
            if content_id == self._last_handled_content_id:
                logger.info(f"Content {content_id} already being handled, skipping duplicate request")
                return True
                
            # Track that we're handling this content ID
            self._last_handled_content_id = content_id
            
            # Get content info
            response = requests.get(f"{self.server_url}/api/content/{content_id}")
            if response.status_code != 200:
                logger.error(f"Failed to get content info: {response.text}")
                self._last_handled_content_id = None  # Reset to allow retry
                return False
            
            content_info = response.json()
            
            # Download the content file if needed
            file_path = self.ensure_content_downloaded(content_id, content_info)
            if not file_path:
                return False
            
            # Call the content callback if provided
            if self.content_callback:
                self.content_callback(content_id, content_info)
            
            # Reset after delay to prevent immediate duplicate processing
            def reset_handled_id():
                time.sleep(2)  # Wait before allowing reprocessing
                if self._last_handled_content_id == content_id:
                    self._last_handled_content_id = None
            
            # Start thread to reset handler flag after delay
            reset_thread = threading.Thread(target=reset_handled_id)
            reset_thread.daemon = True
            reset_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Error handling content update: {str(e)}")
            self._last_handled_content_id = None  # Reset to allow retry
            return False
    
    def ensure_content_downloaded(self, content_id, content_info):
        """Ensure content is downloaded and available locally
        
        Args:
            content_id: ID of the content
            content_info: Dict containing content information
            
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        file_path = os.path.join(DOWNLOAD_FOLDER, content_info['filename'])
        
        # Check if file already exists
        if os.path.exists(file_path):
            logger.info(f"Content file already exists: {file_path}")
            return file_path
        
        # Download the file
        try:
            logger.info(f"Downloading content: {content_info['name']}")
            response = requests.get(
                f"{self.server_url}/api/content/{content_id}/file", 
                stream=True
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to download content: {response.text}")
                return None
            
            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded content to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error downloading content: {str(e)}")
            return None
    
    def send_status_update(self, status, content_id, message=None):
        """Send status update to server
        
        Args:
            status: Status string (e.g., 'playing', 'error')
            content_id: ID of the content being played
            message: Optional status message
        """
        if not self.client_id:
            logger.warning("No client ID available, skipping status update")
            return False
            
        status_data = {
            'client_id': self.client_id,
            'status': status,
            'content_id': content_id
        }
        
        if message:
            status_data['message'] = message
            
        # Try socket.io first if available
        if self.socket and self.socket_connected:
            try:
                self.socket.emit('status_update', status_data)
                return True
            except Exception as e:
                logger.error(f"Failed to send status update via socket: {str(e)}")
        
        # HTTP fallback
        try:
            response = requests.post(
                f"{self.server_url}/api/client/{self.client_id}",
                json=status_data
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send status update via HTTP: {str(e)}")
            return False