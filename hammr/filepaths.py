"""
Replaces py2 GeneralPaths.py, primarily by using the pathlib module and object-oriented paths.
py2 also contained a handful of constants that already exist in places that make more sense,
so I've omitted them.
Note that Path / str is Path
"""

from pathlib import Path


# TODO These really belong elsewhere, like system_config (except system_config is more like instruments_config)
CONTROL_SERVER_IP ='127.0.0.1'
CONTROL_SERVER_PORT = 9022

# Project folder
code = Path(__file__).parent
project = code.parent
configs = project / 'config'

# genericserver and genericclient filepaths
generic_server_script = code / 'genericserver.py'
generic_client_script = code / 'genericclient.py'

# Output folder structure
top = project / 'AcqSystem'
configs_path = top / 'Configs'
data_path = top / 'Data'
logs_path = top / 'Logs'

configstmp_path = configs_path / 'tmp'
h5data_path = data_path / 'h5_files'


# Methods to verify and debug
def check_structure():
    for path in [top, configs_path, data_path, logs_path, configstmp_path, h5data_path]:
        path.mkdir(exist_ok=True)
    print("Folder structure is set up")


def print_tree(root):
    print("-"*20, f"\nFolder structure in {root.parent}")
    print(root.stem)
    for path in sorted(root.rglob('*')):
        depth = len(path.relative_to(root).parts)
        spacer = "- " * depth
        if path.is_dir():
            print(spacer + path.name)
    print("-" * 20)


# Not an ifmain so this will run whenever the module is imported
# check_structure()
print(configs)