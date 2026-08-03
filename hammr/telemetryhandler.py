"""Handler for thermistor data for the purposes of monitoring system temps.

Data begins streaming when the AMR server script is run. This handler should be included then as a monitor for whenever the system is running.
Include the handler into `instruments.SerialTransportThermistors`.
"""


from dotenv import load_dotenv
import os
import paho.mqtt.client as mqtt
import time


load_dotenv()
BROKER = os.getenv("MQTT_BROKER", "")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
PORT = os.getenv("MQTT_PORT")
CERTIFICATE = os.getenv("MQTT_CERT")
topic = "python/mqtt"


class ThermistorTelemetryHandler:
    def __init__(self):
        self.hot_threshold = 0.321  # lower voltage is hotter. 0.321 V = 50 *C
        self.hot_thresholds = [
            0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,
            0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,
            0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,
            0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,
            0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,
        ]


    def connect_mqtt(self, broker, port, username, password):
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                print("Connected")
            else:
                print(f"Connection failed, return code {reason_code}")

        client = mqtt.Client(
            client_id='csu',
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        client.on_connect = on_connect
        client.username_pw_set(USERNAME, PASSWORD)
        client.tls_set(CERTIFICATE)
        client.connect(BROKER, int(PORT))
        return client


    def publish(self, client, topic):
        msg_count = 1
        while True:
            time.sleep(1)
            msg = f"messages: {msg_count}"
            result = client.publish(topic, msg)
            status = result[0]
            if status == 0:
                print(f"Sent `{msg}` to topic `{topic}`")
            else:
                print(f"Failed to send message to topic `{topic}`")
            msg_count += 1
            if msg_count > 5:
                break


    def run(self):
        cl = self.connect_mqtt(BROKER, PORT, USERNAME, PASSWORD)
        cl.loop_start()
        self.publish(cl, 'python/mqtt')
        cl.loop_stop()
        cl.disconnect()
