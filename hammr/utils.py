"""
Generic  methods.
"""
import csv
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

from filepaths import PATH_TO_CONFIGS

load_dotenv()
LOGS_PATH = Path( os.path.expandvars(os.getenv('LOGS_PATH')) )


def create_timestamp() -> str:
    """
    Returns a formatted timestamp string.
    """
    return datetime.now().strftime('%y_%m_%d__%H_%M_%S__')


def create_log(filename="newlog.log", title="ACQSystem", timestamp=True, level=logging.INFO) -> logging.Logger:
    """
    Called in various places to make a log with consistent formatting.
    """
    if not filename.endswith('.log'):
        filename += '.log'

    if timestamp:
        filename = create_timestamp() + filename
    
    logging.basicConfig(
        level = level,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = LOGS_PATH / filename,
        filemode = 'a',
    )
    log = logging.getLogger(title)
    log.addHandler(logging.StreamHandler())  # Logged events are also printed TODO Can stream handlers be different levels?
    log.info(f"Welcome to {title}")

    return log


def write_to_log(
    log: logging.Logger | None,
    message: str,
    level: str = 'info'
) -> None:
    if not log:
        print(f"(NO LOG) {level}: {message}")
        return
    match level:
        case 'debug':
            log.debug(message)
        case 'info':
            log.info(message)
        case 'warn':
            log.warn(message)
        case 'error':
            log.error(message)


def get_thermistor_str(filename='thermistors.csv') -> str:
    """
    Called by L0b processor to create a long metadata string of thermistor labels.
    Assumes a line of headers followed by lines of data. Ignores lines starting with `#`.
    """
    s = ''
    with open(PATH_TO_CONFIGS/filename, 'r', newline='') as f:  # newline='' for csv reader
        reader = csv.reader(f, delimiter=',')
        i = 0
        for row in reader:
            if row[0].startswith('#'):
                continue

            if i == 0:
                # Column headers. Excluded to match previous, but could probably be included w/o issue
                pass
            else:
                s += f'thermistorName[{i}] = "{row[3].strip()}"\n'
            i += 1
    return s


class ThermistorTelemetryHandler:
    def __init__(self):
        self.datasets = []
        self.max_len = 20
        self.number_of_thermistors = 40

        self.hot_threshold = 0.14  # lower voltage is hotter  # 0.14 should be ~350 K


    def add_and_process(self, data: bytes) -> None:
        self.add_dataset(data)
        averages = self.average_voltages()
        self.process_voltages(averages)


    def add_dataset(self, data: bytes) -> None:
        self.datasets.append([float(x) for x in data.decode().split('+')[1:]])
        if len(self.datasets) > self.max_len:
            self.datasets.pop(0)

    
    def average_voltages(self) -> list[float]:
        """Return a simple mean of each thermistor"""
        result = []
        for v in range(self.number_of_thermistors):
            total = 0
            for dataset in self.datasets:
                total += dataset[v]
            result.append(total / self.number_of_thermistors)
        return result
    

    def process_voltages(self, voltages: list[float]) -> None:
        for v in voltages:
            if v < self.hot_threshold:
                self.handle_hot()


    def handle_hot(self) -> None:
        print("Too hot!?")