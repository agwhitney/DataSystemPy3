"""
Replaces py2 GeneralPaths.py, primarily by using the pathlib module and object-oriented paths.
py2 also contained a handful of constants that already exist in places that make more sense, so I've omitted them.
Note that Path / str is Path
"""
import platform
from pathlib import Path


# TODO These really belong elsewhere, like system_config (except system_config is more like instruments_config)
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

# Output folder structure
ACQ = project / 'AcqSystem'

## One of these two is redundant
ACQ_CONFIGS = ACQ / 'configs'
ACQ_CONFIGS_TMP = ACQ_CONFIGS / 'tmp'

ACQ_DATA = ACQ / 'data'
ACQ_DATA_H5 = ACQ_DATA / 'h5_files'

ACQ_LOGS = ACQ / 'logs'


# Verifying and Debugging methods
def check_structure():
    """Validate that the ACQ folder structure exists (by creating it if it doesn't)"""
    for path in [ACQ, ACQ_CONFIGS, ACQ_DATA, ACQ_LOGS, ACQ_CONFIGS_TMP, ACQ_DATA_H5]:
        path.mkdir(exist_ok=True)
    print("Folder structure is set up")


def print_tree(root=ACQ):
    """Visualize a file tree (dirs only)"""
    print("-"*20, f"\nFolder structure in {root}")
    print(root.stem)
    for path in sorted(root.rglob('*')):
        depth = len(path.relative_to(root).parts)
        spacer = "- " * depth
        if path.is_dir():
            print(spacer + path.name)
    print("-" * 20)


# Not an ifmain so this will run whenever the module is imported
check_structure()