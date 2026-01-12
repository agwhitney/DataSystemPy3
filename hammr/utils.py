"""
Generic  methods.
"""
import csv
import logging
from datetime import datetime

from filepaths import ACQ_LOGS, PATH_TO_CONFIGS


def create_timestamp() -> str:
    """
    Returns a formatted timestamp string.
    """
    return datetime.now().strftime('%y_%m_%d__%H_%M_%S__')


def create_log(filename="newlog.log", title="ACQSystem", timestamp=True) -> logging.Logger:
    """
    Called in various places to make a log with consistent formatting.
    """
    if not filename.endswith('.log'):
        filename += '.log'

    if timestamp:
        filename = create_timestamp() + filename
    
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
