""" Replaces GeneralPaths.py and uses Path objects.
The savedata structure is moved to .env and included in scripts using python-dotenv.
This makes it a little cleaner, I think, and more intuitive to the end-user.
"""
import platform
from pathlib import Path


# TODO These really belong elsewhere, like system_config (except system_config is more like instruments_config)
# This is the MasterServer info
CONTROL_SERVER_IP ='127.0.0.1'
CONTROL_SERVER_PORT = 9022

# Source code and Project folder
code = Path(__file__).parent
project = code.parent
PATH_TO_CONFIGS = project / 'config'

# genericserver and genericclient filepaths
PATH_TO_GENSERVER = code / 'genericserver.py'
PATH_TO_GENCLIENT = code / 'genericclient.py'

# Handle differences between Linux and Windows systems
# SERIAL_PORT is used to refer to the correct item in system config.
system = platform.system()
if system == 'Windows':
    PATH_TO_PYTHON = project / '.venv/Scripts/python'
    SERIAL_PORT = 'portWindows'
elif system == 'Linux':
    PATH_TO_PYTHON = project / '.venv/bin/python'
    SERIAL_PORT = 'portLinux'
