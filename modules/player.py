"""
Media Player Module for LED Wall Client
Handles media playback using FFplay
"""
import os
import time
import logging
import subprocess
import threading
import shutil
import platform

logger = logging.getLogger("led_client.player")

class MediaPlayer:
    """Handles media playback with FFplay"""
    
    def __init__(self, config_manager):
        """Initialize the media player
        
        Args:
            config_manager: The configuration manager instance
        """
        self.config = config_manager
        self.player_process = None
        self.is_windows = platform.system() == "Windows"
        self.is_raspberry_pi = self.config._detect_raspberry_pi()
    
    def is_ffplay_available(self):
        """Check if ffplay is available in the system PATH"""
        return shutil.which("ffplay") is not None
    
    def play(self, file_path, content_info, callback=None):
        """Play media content using ffplay with platform-specific optimizations
        
        Args:
            file_path: Path to the media file to play
            content_info: Dict containing info about the content
            callback: Optional callback to execute when playback ends
        
        Returns:
            bool: True if playback started successfully, False otherwise
        """
        try:
            # Check if ffplay is available
            if not self.is_ffplay_available():
                logger.error("FFplay is not installed. Cannot play media content.")
                return False
                
            width = self.config.width
            height = self.config.height
            
            # Base command for all platforms
            cmd = [
                'ffplay', 
                '-x', str(width), 
                '-y', str(height),
                '-alwaysontop',
                '-noborder',
                '-loop', '0',  # Loop continuously
                '-window_title', 'LEDWallPlayer',
                '-left', '0',   # Position window at top-left
                '-top', '0'     # Position window at top-left
            ]
            
            # Add video scaling filter (works on all platforms)
            cmd.extend([
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=disable'
            ])
            
            # Add the file path
            cmd.append(file_path)
            
            logger.info(f"Starting player with command: {' '.join(cmd)}")
            
            # Stop any existing playback
            self.stop()
            
            # For Linux/Raspberry Pi, use different approach to avoid console spam
            if not self.is_windows:
                # Redirect output to /dev/null on Linux/Raspberry Pi
                with open(os.devnull, 'w') as devnull:
                    self.player_process = subprocess.Popen(
                        cmd, 
                        stdout=devnull, 
                        stderr=devnull,
                        start_new_session=True  # Detach from parent process
                    )
                
                # On Raspberry Pi, use a method to move window to top-left corner
                if self.is_raspberry_pi:
                    try:
                        # Allow ffplay window to initialize before moving it
                        time.sleep(1)
                        # Use xdotool to move window (must be installed on Raspberry Pi)
                        if shutil.which('xdotool'):
                            move_cmd = [
                                'xdotool', 'search', '--name', 'LEDWallPlayer', 
                                'windowmove', '0', '0', 'windowactivate'
                            ]
                            subprocess.Popen(move_cmd)
                    except Exception as e:
                        logger.warning(f"Could not position window: {str(e)}")
            else:
                # Windows version
                self.player_process = subprocess.Popen(cmd)
                # Position window properly on Windows
                self._position_window_windows()
            
            # Start monitor thread to detect when playback ends
            monitor_thread = threading.Thread(
                target=self._monitor_playback, 
                args=(content_info, callback)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Error playing content: {str(e)}")
            return False
    
    def _position_window_windows(self):
        """Position the window at 0,0 and enable cursor hiding (Windows only)"""
        if not self.is_windows:
            return
            
        try:
            # Using PowerShell to position the window
            position_cmd = [
                'powershell',
                '-command',
                """
                Start-Sleep -Milliseconds 500
                
                # Add necessary types for window functions
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    
                    public class WindowHelper {
                        [DllImport("user32.dll")]
                        public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
                        
                        [DllImport("user32.dll")]
                        public static extern bool ShowCursor(bool bShow);
                        
                        [DllImport("user32.dll")]
                        public static extern bool GetCursorPos(out POINT lpPoint);
                        
                        [DllImport("user32.dll")]
                        public static extern IntPtr WindowFromPoint(POINT Point);
                        
                        [StructLayout(LayoutKind.Sequential)]
                        public struct POINT {
                            public int X;
                            public int Y;
                        }
                    }
"@

                # Find the player window
                $w = (Get-Process | Where-Object {$_.MainWindowTitle -eq 'LEDWallPlayer'} | Select-Object -First 1)
                
                if ($w) {
                    # Position the window at 0,0 and on top
                    [WindowHelper]::SetWindowPos($w.MainWindowHandle, -1, 0, 0, """ + str(self.config.width) + """, """ + str(self.config.height) + """, 0x0040)
                    
                    # Start a background job to hide cursor when over the player window
                    $job = Start-Job -ScriptBlock {
                        param($windowTitle, $width, $height)
                        Add-Type @"
                            using System;
                            using System.Runtime.InteropServices;
                            
                            public class WindowHelper {
                                [DllImport("user32.dll")]
                                public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
                                
                                [DllImport("user32.dll")]
                                public static extern bool ShowCursor(bool bShow);
                                
                                [DllImport("user32.dll")]
                                public static extern bool GetCursorPos(out POINT lpPoint);
                                
                                [DllImport("user32.dll")]
                                public static extern IntPtr WindowFromPoint(POINT Point);
                                
                                [StructLayout(LayoutKind.Sequential)]
                                public struct POINT {
                                    public int X;
                                    public int Y;
                                }
                            }
"@
                        while ($true) {
                            # Check if window still exists
                            $w = (Get-Process | Where-Object {$_.MainWindowTitle -eq $windowTitle} | Select-Object -First 1)
                            if (-not $w) {
                                # Window closed, exit the loop
                                break
                            }
                            
                            # Get cursor position
                            $point = New-Object WindowHelper+POINT
                            [WindowHelper]::GetCursorPos([ref]$point)
                            
                            # Check if cursor is over the player (top-left corner within dimensions)
                            if ($point.X -ge 0 -and $point.X -lt $width -and $point.Y -ge 0 -and $point.Y -lt $height) {
                                # Hide cursor
                                [WindowHelper]::ShowCursor($false) | Out-Null
                            } else {
                                # Show cursor
                                [WindowHelper]::ShowCursor($true) | Out-Null
                            }
                            
                            # Sleep to reduce CPU usage
                            Start-Sleep -Milliseconds 50
                        }
                        
                        # Ensure cursor is visible when exiting
                        [WindowHelper]::ShowCursor($true) | Out-Null
                    } -ArgumentList 'LEDWallPlayer', """ + str(self.config.width) + """, """ + str(self.config.height) + """
                }
                """
            ]
            subprocess.Popen(position_cmd)
        except Exception as e:
            logger.warning(f"Error positioning window with PowerShell: {str(e)}")
    
    def hide(self):
        """Hide the player window (platform-specific implementation)"""
        if not self.player_process:
            return
            
        try:
            if self.is_windows:
                # Windows-specific implementation using PowerShell
                hide_cmd = [
                    'powershell', 
                    '-command', 
                    "(Get-Process | Where-Object {$_.MainWindowTitle -eq 'LEDWallPlayer'} | ForEach-Object { $showWindowAsync = Add-Type -MemberDefinition '[DllImport(\"user32.dll\")]public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);' -Name Win32ShowWindowAsync -Namespace Win32Functions -PassThru; $showWindowAsync::ShowWindowAsync($_.MainWindowHandle, 2) })"
                ]
                subprocess.run(hide_cmd)
            elif self.is_raspberry_pi:
                # Raspberry Pi implementation using xdotool
                if shutil.which('xdotool'):
                    hide_cmd = ['xdotool', 'search', '--name', 'LEDWallPlayer', 'windowminimize']
                    subprocess.run(hide_cmd)
                else:
                    logger.warning("xdotool not available for window manipulation on Raspberry Pi")
            
            logger.info("Player window hidden")
        except Exception as e:
            logger.error(f"Error hiding player: {str(e)}")
    
    def show(self):
        """Show the player window (platform-specific implementation)"""
        if not self.player_process:
            return
            
        try:
            if self.is_windows:
                # Windows-specific implementation using PowerShell
                show_cmd = [
                    'powershell', 
                    '-command', 
                    "(Get-Process | Where-Object {$_.MainWindowTitle -eq 'LEDWallPlayer'} | ForEach-Object { $showWindowAsync = Add-Type -MemberDefinition '[DllImport(\"user32.dll\")]public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);' -Name Win32ShowWindowAsync -Namespace Win32Functions -PassThru; $showWindowAsync::ShowWindowAsync($_.MainWindowHandle, 9) })"
                ]
                subprocess.run(show_cmd)
            elif self.is_raspberry_pi:
                # Raspberry Pi implementation using xdotool
                if shutil.which('xdotool'):
                    show_cmd = ['xdotool', 'search', '--name', 'LEDWallPlayer', 'windowactivate']
                    subprocess.run(show_cmd)
                else:
                    logger.warning("xdotool not available for window manipulation on Raspberry Pi")
            
            logger.info("Player window restored")
        except Exception as e:
            logger.error(f"Error showing player: {str(e)}")
    
    def _monitor_playback(self, content_info, callback=None):
        """Monitor media playback and restart if needed
        
        Args:
            content_info: Dict containing info about the content
            callback: Optional callback to execute when playback ends
        """
        # Store a local reference to the process to avoid it becoming None during execution
        process = self.player_process
        
        if not process:
            logger.warning("Monitor thread started but player_process is None")
            return
            
        try:
            # Wait for player process to finish
            process.wait()
            
            # After wait completes, check if process is still valid
            # (it might have been changed by another thread)
            if process == self.player_process:
                # Process is still the current one
                exit_code = process.returncode
                logger.warning(f"Player exited with code {exit_code}")
                
                # Execute callback if provided
                if callback:
                    callback(content_info, exit_code)
        except Exception as e:
            logger.error(f"Error monitoring playback: {str(e)}")
    
    def stop(self):
        """Stop the current player process"""
        if not self.player_process:
            return
            
        logger.info("Stopping current player...")
        
        try:
            # Different process termination approaches based on platform
            if self.is_windows:
                # On Windows, we can use the process API directly
                self.player_process.terminate()
                try:
                    self.player_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.player_process.kill()
            else:
                # On Linux/Raspberry Pi, kill by window title to be more reliable
                if self.is_raspberry_pi and shutil.which('xdotool'):
                    # Use xdotool to find and kill the ffplay window
                    kill_cmd = "xdotool search --name LEDWallPlayer windowkill"
                    subprocess.run(kill_cmd, shell=True)
                else:
                    # Fallback to normal process termination
                    self.player_process.terminate()
                    try:
                        self.player_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.player_process.kill()
        except Exception as e:
            logger.error(f"Error stopping player: {str(e)}")
        finally:
            self.player_process = None