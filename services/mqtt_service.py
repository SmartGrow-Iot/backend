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
        self.client = mqtt.Client(client_id="", protocol=mqtt_client.MQTTv5)
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

    def publish_actuator_command(self, zone: str, action: str = "on"):

        if not self.client.is_connected():
            logger.info("MQTT Client is not connected. Cannot publish.")
            return

        topic = f"{ADA_USERNAME}/feeds/{zone}-welcome-feed"
        # topic = f"{ADA_USERNAME}/feeds/smartgrow.{actuator_type}.{zone}"
        result = self.client.publish(topic, action)
        if result.rc == 0:
            logger.info(f"Sent `{action}` to `{topic}`")
        else:
            logger.info(f"Failed to publish to `{topic}`")


# Create a single, shared instance of the MQTT client for the application
mqtt_client = MQTTClient()