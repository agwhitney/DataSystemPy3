import sys
import json

from ..fpga import FPGA
from ..filepaths import PATH_TO_CONFIGS


def send_config(config: dict):

    fpga = FPGA(config, log=None)
    fpga.configure()
    fpga.reset_hardware()
    fpga.disconnect_tcp()



if __name__ == '__main__':
    try:
        config = sys.argv[1]
    except IndexError:
        config = 'system.json'

    config_path = PATH_TO_CONFIGS / config
    with open(config_path, 'r') as f:
        config = json.load(f)

    send_config()