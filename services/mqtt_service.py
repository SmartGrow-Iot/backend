from paho.mqtt import client as mqtt_client
import logging
from dotenv import load_dotenv
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mqtt_service")

# Load environment variables
load_dotenv()
ADA_BROKER = os.getenv("ADA_BROKER")
ADA_PORT = os.getenv("ADA_PORT")
ADA_USERNAME = os.getenv("ADA_USERNAME")
ADA_KEY = os.getenv("ADA_KEY")

client = mqtt_client.Client(client_id="", protocol=mqtt_client.MQTTv5)
client.username_pw_set(ADA_USERNAME, ADA_KEY)

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to Adafruit IO")
        else:
            logger.info(f"MQTT connection failed, code {rc}")

    client.on_connect = on_connect
    client.connect(ADA_BROKER, int(ADA_PORT))
    client.loop_start()

def publish_actuator_command(zone: str, action: str = "on"):
    topic = f"{ADA_USERNAME}/feeds/{zone}.welcome-feed"
    # topic = f"{ADA_USERNAME}/feeds/smartgrow.{actuator_type}.{zone}"
    result = client.publish(topic, action)
    if result.rc == 0:
        logger.info(f"Sent `{action}` to `{topic}`")
    else:
        logger.info(f"Failed to publish to `{topic}`")
