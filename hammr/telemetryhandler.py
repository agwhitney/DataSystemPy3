"""Handler for thermistor data for the purposes of monitoring system temps.

Data begins streaming when the AMR server script is run. This handler should be included then as a monitor for whenever the system is running.
Include the handler into `instruments.SerialTransportThermistors`.
"""


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