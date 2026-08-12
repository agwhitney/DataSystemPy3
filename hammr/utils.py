"""Useful methods called in various places."""
import csv
import logging
import os

from datetime import datetime
from dotenv import load_dotenv
from numpy import log
from pathlib import Path
from typing import Literal

from filepaths import PATH_TO_CONFIGS

def validate_variable(key: str) -> str:
    """Gets `key` from environment and expands variables. If None is returned, raises an error suggesting what to do."""
    env_value = os.getenv(key)
    if not env_value:
        raise RuntimeError(f"{key} is not defined in the environment. Check the .env file and run scripts/init_acq_folders.py if needed.")
    value = os.path.expandvars(env_value)
    return value

load_dotenv()
LOGS_PATH = Path( validate_variable('LOGS_PATH') )




def create_timestamp() -> str:
    """Returns a formatted timestamp string: 'yy_mm_dd__hh_mm_ss__'"""
    return datetime.now().strftime('%y_%m_%d__%H_%M_%S__')


def create_log(filename="newlog.log", title="ACQSystem", prepend_timestamp=True, level=logging.INFO) -> logging.Logger:
    """Returns a logger object pointing to a log file.

    By default, a log will be created called "{timestamp}{filename}.log" and will record at INFO level.
    Logged messages will also be printed in STDOUT.

    Args:
        `filename`: Name of the file to log to. Will be appended with '.log' if not provided.
        `title`: Name of the logger. Not really used.
        `prepend_timestamp`: If True, include a timestamp before `filename`.
        `level`: The logging level to record.

    Returns:
        A log.
    """
    if not filename.endswith('.log'):
        filename += '.log'

    if prepend_timestamp:
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
    level: Literal['debug', 'info', 'warn', 'error'] = 'info'
) -> None:
    """Write to a given log or, if log is None, print the message.

    Args:
        `log`: The log to write to. If None, prints.
        `message`: The message to log or print.
        `level`: The logging level to record at.    
    """
    if not log:
        print(f"(NO LOG) {level}: {message}")
        return
    match level:
        case 'debug':
            log.debug(message)
        case 'info':
            log.info(message)
        case 'warn':
            log.warning(message)
        case 'error':
            log.error(message)


def get_thermistor_str(filename='thermistors.csv') -> str:
    """Called by L0b processor to create a long metadata string of thermistor labels.
    Assumes a line of headers followed by lines of data. Ignores lines starting with `#`.
    """
    s = ''
    with open(PATH_TO_CONFIGS/filename, 'r', newline='') as f:  # newline='' for csv reader
        reader = csv.reader(f, delimiter=',')
        i = 0
        for row in reader:
            if row[0].startswith('#'):
                continue

            if i == 0:  # Column headers. Excluded to match previous, but could probably be included w/o issue
                pass
            else:
                s += f'thermistorName[{i}] = "{row[3].strip()}"\n'
            i += 1
    return s


def voltage2kelvin(model: Literal['KS502J2', '44906'], voltage: float) -> float:
    """Converts voltage to kelvin per model of thermistor.
    
    In practice, the thermistors are nearly identical.
    """
    match model:
        case 'KS502J2':
            A = 1.29337828808 * 10**-3
            B = 2.34313147501 * 10**-4
            C = 1.09840791237 * 10**-7
            D = -6.51108048031 * 10**-11
        case '44906':
            A = 1.28082086269172 * 10**-3
            B = 2.36865057309759 * 10**-4
            C = 9.02634799967035 * 10**-8
            D = 0
    regulated_V = 1.12  # 1.06 in code metadata, 1.12 in L0b word doc
    resist = 5000 * (voltage / (regulated_V - voltage))
    temp = 1 / (A + B*log(resist) + C*log(resist)**3 + D*log(resist)**5)
    return temp