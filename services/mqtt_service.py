import json
import os
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import logging
from firebase_config import initialize_firebase_admin, get_firestore_db

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mqtt_service")

# Load environment variables from .env file
load_dotenv()
ADA_BROKER = os.getenv("ADA_BROKER")
ADA_PORT = int(os.getenv("ADA_PORT"))
ADA_USERNAME = os.getenv("ADA_USERNAME")
ADA_KEY = os.getenv("ADA_KEY")

initialize_firebase_admin()
db = get_firestore_db()


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

    def publish_actuator_status(self, zone: str, action: str):
        """
        Publishes a specific command for an actuator type to a consolidated zone feed.

        Args:
            zone (str): The zone of the actuator (e.g., 'zone1').
            action (str): The type of action (e.g., 'water_on', 'water_off', 'fan_on').
        """
        if not self.client.is_connected():
            logger.info("MQTT Client is not connected. Cannot publish.")
            return

        action_to_key_map = {
            "water_on": {"pump": "ON"},
            "water_off": {"pump": "OFF"},
            "light_on": {"light": "ON"},
            "light_off": {"light": "OFF"},
            "fan_on": {"fan": "ON"},
            "fan_off": {"fan": "OFF"},
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
            logger.error(f"Invalid action type: '{action}'. No corresponding payload found.")
            return
        if not group:
            logger.error(f"Invalid zone: '{zone}'. No zone found.")
            return

        # Other two actuator status are whatever existing values at the ESP32 side
        payload = json.dumps(payload_key)

        topic = f"{ADA_USERNAME}/feeds/{group}.actuator-status"
        result = self.client.publish(topic, payload)
        if result.rc == 0:
            logger.info(f"Sent `{payload}` to `{topic}`")
        else:
            logger.info(f"Failed to publish to `{topic}`")

    def subscribe_actuator_feedback(self):
        """
        Subscribes to actuator status feed and logs data to Firestore.
        """

        if not self.client.is_connected():
            logger.info("MQTT Client is not connected. Cannot subscribe.")
            return

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())

                logger.info(f"Received message on topic `{msg.topic}`: {payload}")

                # Three key fields interested
                if "action" not in payload and "group" not in payload and "timestamp" not in payload:
                    logger.info("Incomplete payload.")
                    return

                action_to_key_map = {
                    "pump ON": "water_on",
                    "pump OFF": "water_off",
                    "fan ON": "fan_on",
                    "fan OFF": "fan_off",
                    "light ON": "light_on",
                    "light OFF": "light_off",
                }
                action_to_actuator_map = {
                    "pump ON": "waterActuator",
                    "pump OFF": "waterActuator",
                    "fan ON": "fanActuator",
                    "fan OFF": "fanActuator",
                    "light ON": "lightActuator",
                    "light OFF": "lightActuator",
                }
                group_to_zone_map = {
                    "group-1": "zone1",
                    "group-2": "zone2",
                    "group-3": "zone3",
                    "group-4": "zone4"
                }

                # Get actuator and plants based on zone
                zone = group_to_zone_map[payload.get("group")]

                # Process payload to log data
                action = action_to_key_map[payload.get("action")]
                actuator = action_to_actuator_map[payload.get("action")]

                zone_doc = db.collection("ZoneInfo").document(zone).get()
                zone_data = zone_doc.to_dict()
                actuator_id = zone_data.get(actuator)

                docs = db.collection("Plants").where("zone", "==", zone).stream()
                plants = [doc.to_dict() for doc in docs]

                trigger = "auto"
                triggerBy = "SYSTEM"
                timestamp = payload.get("timestamp")

                for plant in plants:
                    action_log = {
                        "action": action,
                        "actuatorId": actuator_id,
                        "plantId": plant['plantId'],
                        "trigger": trigger,
                        "triggerBy": triggerBy,
                        "timestamp": timestamp
                    }
                    generated_id = db.collection("ActionLog").document().id
                    doc_id = f"action_{generated_id}"
                    db.collection("ActionLog").document(doc_id).set(action_log)

            except Exception as e:
                logger.error(f"Error processing incoming MQTT message: {e}")

        self.client.on_message = on_message

        group_feeds = [
            "group-1.actuator-feedback",
            "group-2.actuator-feedback",
            "group-3.actuator-feedback",
            "group-4.actuator-feedback"
        ]
        for feed in group_feeds:
            full_topic = f"{ADA_USERNAME}/feeds/{feed}"
            self.client.subscribe(full_topic)
            logger.info(f"Subscribed to topic: {full_topic}")


# Create a single, shared instance of the MQTT client for the application
mqtt_client = MQTTClient()
