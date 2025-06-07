import requests
import json
import time
import logging
import threading
import asyncio
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rest_device_service")

# Load environment variables
load_dotenv()

# REST Device Service Configuration
DEVICE_API_BASE_URL = os.getenv("DEVICE_API_BASE_URL", "http://localhost:8080")
DEVICE_API_TIMEOUT = int(os.getenv("DEVICE_API_TIMEOUT", 10))
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "")

class RestDeviceService:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RestDeviceService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if RestDeviceService._initialized:
            return
            
        # Device registry (maps device_id to device URL)
        self.devices = {}
        
        # Command results storage
        self.command_results = {}
        
        # Load known devices from config or database
        self._load_known_devices()
        
        RestDeviceService._initialized = True
    
    def _load_known_devices(self):
        """Load device registry from configuration or database"""
        # You could load this from a database in the future
        # For now, we'll use a simple in-memory dictionary
        # Format: device_id -> device_url
        self.devices = {
            "device001": f"{DEVICE_API_BASE_URL}/devices/device001",
            "device002": f"{DEVICE_API_BASE_URL}/devices/device002",
            # Add more devices as needed
        }
        logger.info(f"Loaded {len(self.devices)} devices from configuration")
    
    def register_device(self, device_id: str, device_url: str):
        """Register a new device or update existing device URL"""
        self.devices[device_id] = device_url
        logger.info(f"Registered device {device_id} at {device_url}")
    
    def send_command(self, device_id: str, command: str, params: Optional[Dict[str, Any]] = None,
                    callback: Optional[Callable] = None, timeout: int = DEVICE_API_TIMEOUT):
        """
        Send command to device via REST API
        
        Args:
            device_id: Target device ID
            command: Command to execute
            params: Command parameters
            callback: Function to call when response is received
            timeout: Command timeout in seconds
            
        Returns:
            str: Message ID of the sent command
        """
        # Check if device exists
        if device_id not in self.devices:
            logger.error(f"Device {device_id} not found in registry")
            return None
        
        # Generate unique message ID
        message_id = f"{int(time.time())}_{device_id}"
        
        # Prepare request payload
        payload = {
            "message_id": message_id,
            "command": command,
            "timestamp": int(time.time())
        }
        
        if params:
            payload["params"] = params
        
        # Prepare request headers
        headers = {
            "Content-Type": "application/json"
        }
        
        if DEVICE_API_KEY:
            headers["X-API-Key"] = DEVICE_API_KEY
        
        # Create a thread to send the request asynchronously
        def send_request():
            try:
                device_url = self.devices[device_id]
                logger.info(f"Sending command to {device_id} at {device_url}: {command}")
                
                response = requests.post(
                    f"{device_url}/command",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Command sent successfully to {device_id}")
                    
                    # Store result for retrieval
                    self.command_results[message_id] = {
                        "message_id": message_id,
                        "device_id": device_id,
                        "status": "success",
                        "data": result
                    }
                    
                    # Call callback if provided
                    if callback:
                        callback(self.command_results[message_id])
                else:
                    logger.error(f"Error sending command to {device_id}: {response.status_code} {response.text}")
                    error_result = {
                        "message_id": message_id,
                        "device_id": device_id,
                        "status": "error",
                        "data": {
                            "code": response.status_code,
                            "message": response.text
                        }
                    }
                    
                    # Store error result
                    self.command_results[message_id] = error_result
                    
                    # Call callback if provided
                    if callback:
                        callback(error_result)
                        
            except Exception as e:
                logger.error(f"Exception sending command to {device_id}: {e}")
                error_result = {
                    "message_id": message_id,
                    "device_id": device_id,
                    "status": "error",
                    "data": {
                        "message": str(e)
                    }
                }
                
                # Store error result
                self.command_results[message_id] = error_result
                
                # Call callback if provided
                if callback:
                    callback(error_result)
        
        # Start the request in a separate thread
        thread = threading.Thread(target=send_request)
        thread.daemon = True
        thread.start()
        
        return message_id
    
    def get_command_result(self, message_id: str):
        """Get the result of a previously sent command"""
        if message_id in self.command_results:
            return self.command_results[message_id]
        return None

# Create singleton instance
rest_device_service = RestDeviceService()