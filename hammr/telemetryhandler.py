"""Handler for thermistor data for the purposes of monitoring system temps.

Data begins streaming when the AMR server script is run. This handler should be included then as a monitor for whenever the system is running.
Include the handler into `instruments.SerialTransportThermistors`. There, data is broadcast to the AMR client and then handled here.
"""
import json
import paho.mqtt.client as mqtt
import time

from dotenv import load_dotenv
from logging import Logger
from typing import Literal

from filepaths import Pathlike, PATH_TO_CONFIGS
from utils import validate_variable, voltage2kelvin, write_to_log


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
        self.client = self.connect_mqtt(BROKER, int(PORT), USERNAME, PASSWORD, CERTIFICATE)

        # lower voltage is hotter. 0.321 V = 50 *C
        # self.hot_thresholds = [
        #     0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,  # Digitizer 5
        #     0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,  # Digitizer 1
        #     0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,  # Digitizer 2
        #     0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,  # Digitizer 3
        #     0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321, 0.321,  # Digitizer 4
        # ]
        self.hot_thresholds = [
            50, 50, 50, 50, 50, 50, 50, 50,  # Digitizer 5
            50, 50, 50, 50, 50, 50, 50, 50,  # Digitizer 1
            50, 50, 50, 50, 50, 50, 50, 50,  # Digitizer 2
            50, 50, 50, 50, 50, 50, 50, 50,  # Digitizer 3
            50, 50, 50, 50, 50, 50, 50, 50,  # Digitizer 4
        ]


    def __del__(self):
        self.client.disconnect()


    def load_thresholds_from_file(self, filepath: Pathlike | None = None) -> list[float]:
        if not filepath:
            filepath = PATH_TO_CONFIGS / 'thermistors.csv'
        ...


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


    def handle_data(self, data: bytes) -> None:
        voltages = [float(v) for v in data.decode().split('+')[1:]]
        flag: Literal['green', 'red'] = "green"
        flagged_indices = []

        for i, (voltage, threshold) in enumerate(zip(voltages, self.hot_thresholds)):
            index = i + 1
            # timeit suggests that this conversion is two orders of magnitude slower (2.3 s vs 0.3 s in 10k loops)
            temp = voltage2kelvin(model='KS502J2', voltage=voltage) - 273.15
            if temp > threshold:
                flagged_indices.append(index)
                flag = "red"

        telemetry = json.dumps({'temps': voltages, 'flag': flag, 'flagged_indices': flagged_indices})
        if flag == "red":
            write_to_log(self.log, f"Thermistors {flagged_indices} have been flagged as too hot.", level='warn')
        self.publish_mqtt(telemetry)


    def publish_mqtt(self, data: str) -> None:
        self.client.loop_start()
        result = self.client.publish(topic, data)
        status = result[0]
        if status == 0:
            print(f"Sent `{data}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic `{topic}`")
        self.client.loop_stop()