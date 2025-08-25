import serial
import time


def query_channels(conn) -> None:
    """
    Get a response (or timeout) from each connected device.
    """
    for i in range(8):
        time.sleep(0.5)  # I think this is necessary but can be shorter.
        cmd = f'#0{i}\r'
        conn.write(cmd.encode())
        r = conn.readline()
        print(i, r.decode())


if __name__ == '__main__':    
    conn = serial.Serial('COM3', timeout=2)
    query_channels(conn)