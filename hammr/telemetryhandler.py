"""Handler for thermistor data for the purposes of monitoring system temps.

Data begins streaming when the AMR server script is run. This handler should be included then as a monitor for whenever the system is running.
Include the handler into `instruments.SerialTransportThermistors`. There, data is broadcast to the AMR client and then handled here.
"""
import csv
import json
import paho.mqtt.client as mqtt

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
topic = "csu/PayloadTemperatures"


class ThermistorTelemetryHandler:
    def __init__(self, log: Logger | None):
        self.client = self.connect_mqtt(BROKER, int(PORT), USERNAME, PASSWORD, CERTIFICATE)
        self.log = log

        # lower voltage is hotter. 0.321 V = 50 *C
        self.hot_thresholds = self.load_thresholds_from_csv(PATH_TO_CONFIGS / 'thermistors.csv')


    def __del__(self):
        self.client.disconnect()


    def load_thresholds_from_csv(self, filepath: Pathlike) -> list[tuple[int, float]]:
        """Specifically, read the HotThreshold column from config/thermistors.csv

        Returns a sorted list of (index, threshold) tuples. 
        """
        hot_thresholds = []
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f, delimiter=',')
            i = 0
            for row in reader:
                if row[0].startswith('#'):
                    continue

                if i == 0:  # Column headers
                    pass
                else:
                    index = int(row[0].strip()) - 1
                    threshold = float(row[5].strip())
                    hot_thresholds.append((index, threshold))
                i += 1
        hot_thresholds.sort()
        return hot_thresholds


    def handle_data(self, datagram: bytes) -> None:
        """Checks thermistor data and publishes it via MQTT.

        Data are compared as *C to `self.hot_thresholds`. Values outside of thresholds will trigger a flag.
        Data, the overall flag, and the indices that triggered a flag are packaged as JSON and published via MQTT. 

        Args:
            `data`: Combined voltage readings from all thermistors, formatted as floats separated by '+'.
                The acquisition code returns digitizers in the order 5-1-2-3-4 (likely, unintentionally).
        """
        s = datagram.decode()
        data_start = s.find('DATA:') + 5
        data_end = s.find(':ENDS')
        data = s[data_start : data_end]
        voltages = [float(v) for v in data.split('+')[1:]]
        temperatures = [round(voltage2kelvin(model='KS502J2', voltage=v) - 273.15, 2) for v in voltages]
        flag: Literal['green', 'yellow', 'red'] = 'green'
        flagged_thermistors = []

        for temp, values in zip(temperatures, self.hot_thresholds):
            index, threshold = values
            if temp > threshold:
                flagged_thermistors.append((index, temp))
                flag = 'red'

        telemetry = json.dumps({
            'voltages': voltages,
            'temperatures': temperatures,
            'flag': flag,
            'flagged_thermistors': flagged_thermistors,
        })
        write_to_log(self.log, telemetry, 'info')
        self.publish_mqtt(telemetry)


    def connect_mqtt(self, broker, port, username, password, certificate):
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                write_to_log(self.log, "Connected to MQTT broker", 'info')
            else:
                write_to_log(self.log, f"Connection failed, return code {reason_code}", 'error')

        client = mqtt.Client(
            client_id='csu',
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        client.on_connect = on_connect
        client.username_pw_set(username, password)
        client.tls_set(certificate)
        client.connect(broker, port)
        return client


    def publish_mqtt(self, data: str) -> None:
        self.client.loop_start()
        result = self.client.publish(topic, data)
        status = result[0]
        if status == 0:
            write_to_log(self.log, "Telemetry sent to MQTT broker", 'info')
        else:
            write_to_log(self.log, "Failed to send message to MQTT broker", 'error')
        self.client.loop_stop()
