import json
import os
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mqtt_service")

# Load environment variables from .env file
load_dotenv()
ADA_BROKER = os.getenv("ADA_BROKER")
ADA_PORT = int(os.getenv("ADA_PORT"))
ADA_USERNAME = os.getenv("ADA_USERNAME")
ADA_KEY = os.getenv("ADA_KEY")

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="")
        self.client.username_pw_set(ADA_USERNAME, ADA_KEY)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info("MQTT Service: Successfully connected to Adafruit IO Broker.")
        else:
            logger.info(f"MQTT Service: Failed to connect, return code {rc}\n")

    def _on_disconnect(self, client, userdata, rc, properties):
        logger.info("MQTT Service: Disconnected from Adafruit IO Broker.")

    def connect(self):
        try:
            logger.info("MQTT Service: Attempting to connect...")
            self.client.connect(ADA_BROKER, ADA_PORT, 60)
            self.client.loop_start()  # Start a background thread to handle network traffic
        except Exception as e:
            logger.info(f"MQTT Service: Error connecting - {e}")

    def disconnect(self):
        logger.info("MQTT Service: Disconnecting...")
        self.client.loop_stop()
        self.client.disconnect()

    def publish_actuator_command(self, zone: str, action: str):
        """
        Publishes a specific command for an actuator type to a consolidated zone feed.

        Args:
            zone (str): The zone of the actuator (e.g., 'zone1').
            action (str): The type of action ('watering', 'light', 'fan').
        """
        if not self.client.is_connected():
            logger.info("MQTT Client is not connected. Cannot publish.")
            return

        action_to_key_map = {
            "water": "pump",
            "light": "light",
            "fan": "fan"
        }
        zone_to_group_map = {
            "zone1": "group-1",
            "zone2": "group-2",
            "zone3": "group-3",
            "zone4": "group-4"
        }
        payload_key = action_to_key_map.get(action)
        group = zone_to_group_map.get(zone)

        if not payload_key:
            logger.error(f"Invalid action type: '{action}'. No corresponding payload key found.")
            return
        if not group:
            logger.error(f"Invalid zone: '{zone}'. No zone found.")
            return

        # Other two actuator status are whatever existing values at the ESP32 side
        payload_dict = {payload_key: "ON"}
        payload = json.dumps(payload_dict)

        topic = f"{ADA_USERNAME}/feeds/{group}.actuator-status"
        result = self.client.publish(topic, payload)
        if result.rc == 0:
            logger.info(f"Sent `{payload}` to `{topic}`")
        else:
            logger.info(f"Failed to publish to `{topic}`")


# Create a single, shared instance of the MQTT client for the application
mqtt_client = MQTTClient()