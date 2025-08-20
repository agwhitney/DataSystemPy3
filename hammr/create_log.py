"""
Moved this here just to say I did something.
Other util functionscould also make sense here.
"""
import logging
from datetime import datetime

from filepaths import logs_path


def create_log(filename="Log", title="ACQSystem", timestamp=True) -> logging.Logger:
    if not filename.endswith('.log'):
        filename += '.log'

    if timestamp:
        filename = datetime.now().strftime('%y_%m_%d__%H_%M_%S__') + filename
    
    logging.basicConfig(
        level = logging.DEBUG,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = logs_path / filename,
        filemode = 'a',
    )
    log = logging.getLogger(title)
    log.addHandler(logging.StreamHandler())  # Logged events are also printed
    log.info(f"Welcome to {title}")

    return log