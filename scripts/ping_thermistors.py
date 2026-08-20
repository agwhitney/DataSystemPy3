"""Check that the thermistors are connected.

Output will be 8 labeled lines, and you should see data as voltages from 1, 2, 3, 4, 5.
"""
import serial
import time


def query_channels(connpath='/dev/ttyUSB-thm') -> None:
    """
    Get a response (or timeout) from each connected device.
    """
    conn = serial.Serial(connpath, timeout=2)
    for i in range(8):
        time.sleep(0.25)  # I think this is necessary but can be shorter.
        cmd = f'#0{i}\r'
        conn.write(cmd.encode())
        r = conn.readline()
        print(i, r.decode())


if __name__ == '__main__':
    query_channels()