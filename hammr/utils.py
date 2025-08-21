"""
Moved this here just to say I did something.
Other util functionscould also make sense here.
"""
import csv
import logging
from datetime import datetime

from filepaths import ACQ_LOGS, PATH_TO_CONFIGS


def create_log(filename="Log", title="ACQSystem", timestamp=True) -> logging.Logger:
    """
    Called in various places to make a log with consistent formatting.
    """
    if not filename.endswith('.log'):
        filename += '.log'

    if timestamp:
        filename = datetime.now().strftime('%y_%m_%d__%H_%M_%S__') + filename
    
    logging.basicConfig(
        level = logging.DEBUG,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = ACQ_LOGS / filename,
        filemode = 'a',
    )
    log = logging.getLogger(title)
    log.addHandler(logging.StreamHandler())  # Logged events are also printed
    log.info(f"Welcome to {title}")

    return log


def get_thermistor_map(filename='thermistors.csv') -> str:
    """
    Called in datastructures.py to provide a large string of metadata using
    Config/thermistors.csv as reference.
    """
    s = ''
    with open(PATH_TO_CONFIGS/filename, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        for index, row in enumerate(reader):
            # Skip header, and avoid leading/trailing newlines.
            if index == 0:
                continue
            elif index == 1:
                s += f'thermistorName[{index}] = "{row[2].strip()}"'
            else:
                s += f'\nthermistorName[{index}] = "{row[2].strip()}"'
    return s