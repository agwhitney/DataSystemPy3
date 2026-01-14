import socket

address = ('10.10.10.2', 30)

def test_connection():
    """
    I think that during debugging the socket is not closing correctly, and then it gets
    locked on the FPGA side.
    """
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(address)
        print("Success")
        s.close()
        print("Closed")
    except TimeoutError as e:
        s.close()
        print(e)


if __name__ == '__main__':
    test_connection()