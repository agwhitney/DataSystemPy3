"""Handler for thermistor data for the purposes of monitoring system temps.

Data begins streaming when the AMR server script is run. This handler should be included then as a monitor for whenever the system is running.
Include the handler into `instruments.SerialTransportThermistors`.
"""


import paho.mqtt.client as mqtt
import time

from dotenv import load_dotenv
from logging import Logger

from utils import validate_variable, write_to_log


load_dotenv()
BROKER = validate_variable("MQTT_BROKER")
USERNAME = validate_variable("MQTT_USERNAME")
PASSWORD = validate_variable("MQTT_PASSWORD")
PORT = validate_variable("MQTT_PORT")
CERTIFICATE = validate_variable("MQTT_CERT")
topic = "python/mqtt"


class ThermistorTelemetryHandler:
    def __init__(self, log: Logger | None):
        self.log = log
        self.hot_threshold = 0.321  # lower voltage is hotter. 0.321 V = 50 *C
        self.hot_thresholds = {
            1: [0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321],
            2: [0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321],
            3: [0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321],
            4: [0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321],
            5: [0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321],
        }


    def connect_mqtt(self, broker, port, username, password, certificate):
        # TODO is it preferable to connect once and only publish when necessary? Or do both when required?
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
        client.username_pw_set(username, password)
        client.tls_set(certificate)
        client.connect(broker, port)
        return client


    def publish_test(self, client, topic):
        msg_count = 1
        while True:
            time.sleep(1)
            msg = f"test from csu - messages: {msg_count}"
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
        cl = self.connect_mqtt(BROKER, int(PORT), USERNAME, PASSWORD, CERTIFICATE)
        cl.loop_start()
        self.publish_test(cl, topic)
        cl.loop_stop()
        cl.disconnect()


    def check_data(self, digitizer: int, data: bytes) -> None:
        """Takes data line by line (i.e., per digitizer) and checks against thresholds.
        Recall that digitizers are recorded as 5-1-2-3-4. Digitizer is sent as 1--5.
        """
        row = (digitizer + 5) % 5
        voltages = [float(v) for v in data.decode().split('+')[1:]]
        thresholds = self.hot_thresholds[row]

        for i, (voltage, threshold) in enumerate(zip(voltages, thresholds)):
            if voltage < threshold:
                index = (row - 1) * 8 + i
                self.high_temp_alert(index)


    def high_temp_alert(self, index: int):
        msg = f"Temperature at index {index} is above 50 *C"
        write_to_log(self.log, msg, 'warn')

        cl = self.connect_mqtt(BROKER, int(PORT), USERNAME, PASSWORD, CERTIFICATE)
        cl.loop_start()
        result = cl.publish(topic, msg)
        status = result[0]
        if status == 0:
            print(f"Sent `{msg}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic `{topic}`")
        cl.loop_stop()
        cl.disconnect()