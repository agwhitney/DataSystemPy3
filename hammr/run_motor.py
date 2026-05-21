"""
Starts the motor and waits for input before stopping it.
"""
import json

from fpga import FPGA, FPGAConfig
from filepaths import PATH_TO_CONFIGS


with open(PATH_TO_CONFIGS / 'system.json') as f:
    data = json.load(f)['radiometer']

fpgaconfig = FPGAConfig.from_json(PATH_TO_CONFIGS / 'fpga.json')


f = FPGA(data, fpgaconfig, log=None)
print('starting motor')
f.motor_control(f.fpgaconfig.motorstart)
input("press enter to send STOP")
f.motor_control(f.fpgaconfig.motorstop)
f.disconnect_tcp()
