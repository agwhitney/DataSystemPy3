"""
Handy functions for debugging thermistor hardware and output.
"""
import serial
import time

import tables as tb
import numpy as np


def query_channels() -> None:
    """
    Get a response (or timeout) from each connected device.
    """
    conn = serial.Serial('/dev/ttyUSB1', timeout=2)
    for i in range(8):
        time.sleep(0.5)  # I think this is necessary but can be shorter.
        cmd = f'#0{i}\r'
        conn.write(cmd.encode())
        r = conn.readline()
        print(i, r.decode())


def temp_from_h5volt(filepath: str):
    """
    Check that the .h5 output (in volts) is reasonable (in Kelvin)
    """
    def convert(thm_type, voltage):
        if thm_type == 'KS':
            A = 1.29337828808 * 10**-3
            B = 2.34313147501 * 10**-4
            C = 1.09840791237 * 10**-7
            D = -6.51108048031 * 10**-11
        elif thm_type == '44':
            A = 1.28082086269172 * 10**-3
            B = 2.36865057309759 * 10**-4
            C = 0.902634799967035 * 10**-8
            D = 0

        regulated_V = 1.12  # 1.06 in code metadata, 1.12 in L0b word doc
        resist = 5000 * (voltage / (regulated_V - voltage))
        temp = 1 / (A + B*np.log(resist) + C*np.log(resist)**3 + D*np.log(resist)**5)
        return temp

    fp = tb.open_file(filepath, 'r')
    table = fp.root.Temperature_Data.Thermistor_Data
    voltages = table.read()['Voltages']  # numpy array (mmts, thms)
    fp.close()

    temps = convert('44', voltages)
    print(temps[0])


if __name__ == '__main__':
    query_channels()