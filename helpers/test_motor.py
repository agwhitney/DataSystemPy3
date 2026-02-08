"""
Starts the motor and stops it when told.
"""
import json

from hammr.fpga import FPGA
from hammr.filepaths import PATH_TO_CONFIGS
from hammr.utils import create_log

with open(PATH_TO_CONFIGS / 'system.json') as f:
    data = json.load(f)['radiometer']

log = create_log('dummy.log', "Dummy")


f = FPGA(data, log)
print('starting motor')
f.motor_control(f.START_VALUE)
input("press enter to send STOP")
f.motor_control(f.STOP_VALUE)
f.disconnect_tcp()
