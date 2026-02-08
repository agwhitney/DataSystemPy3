from datetime import datetime
import time
import struct


class L0aReader:
    def __init__(self, filename):
        self.line_count = 0
        self.package_flag : bytes
        self.time_flag = b'TIME:'
        self.data_flag = b'DATA:'
        self.stop_flag = b':ENDS\n'

        self.filename = filename


    def parse_file(self, line_limit=0):
        with open(self.filename, 'rb') as file:
            print(file.readline().decode())  # welcome line
            
            remainder = b''
            i = 0
            for line in file:
                i += 1
                if i == line_limit:
                    break

                if line.startswith(self.package_flag):
                    # Start of line
                    data = b''
                    package_number = int(line[
                        line.index(self.package_flag) + len(self.package_flag) : line.index(self.time_flag)
                        ])
                    timestamp = float(line[
                        line.index(self.time_flag) + len(self.time_flag) : line.index(self.data_flag)
                        ])
                    
                    # Complete line
                    if line.endswith(self.stop_flag):
                        data = line[
                            line.index(self.data_flag) + len(self.data_flag) : -len(self.stop_flag)
                            ]

                    # Start of split line
                    else:
                        data = line[
                            line.index(self.data_flag) + len(self.data_flag) :
                            ]
                        continue
                else:
                    # Middle of split line
                    if not line.endswith(self.stop_flag):
                        data += line
                        continue

                    # End of split line
                    else:
                        data += line[ : -len(self.stop_flag) ]

                data = remainder + data
                remainder = self.process_data(package_number, timestamp, data)


        def process_data(self, package_number, timestamp, data) -> bytes:
            print(package_number, timestamp, data)
            return b''


class GPSReader(L0aReader):
    def __init__(self, filename):
        super().__init__(filename)
        self.package_flag = b'PACG:'


    def process_data(self, package_number, timestamp, data) -> bytes:
        """
        The recorded data is a frame from the GPS with the delimiter already trimmed.
        The delimiter was chosen to be the frame end and prefix, see the OEM documentation and instruments.py.
        This leaves the data (46 bytes) plus 2 extra variable bytes from the suffix (CRC16).
        3x float - 3x double - 6x byte 1x uInt - 2x byte
        roll-pitch-yaw lat-lon-alt time crc16
        """
        if len(data) == 48:
            vals = struct.unpack('>fffdddBBBBBBI', data[:46])  # 13 values

            # self.row_pointer['EulerAngles'] = vals[:3]
            # self.row_pointer['Position'] = vals[3:6]
            
            d = datetime(vals[6] + 2000, vals[7], vals[8], vals[9], vals[10], vals[11])
            # XB For testing purposes only, GPS/IMU does only provide time and position if it is receiving GPS satellites
            # self.row_pointer['GPSTime'] = time.mktime(d.timetuple())
            # self.row_pointer['Timestamp'] = timestamp
            # # self.row_pointer['Packagenumber'] = package_number
            # self.row_pointer.append()
            print()
        
        else:
            print(f"GPS data is {len(data)} bytes and should be 48. Skipping this line (instrumentparsers.py).")
            


if __name__ == '__main__':
    g = GPSReader("/home/adam/Desktop/260206_kba/amr/data/26_02_06__14_09_54__2of6_260206_kba_tarmac10ms_GPS-IMU.bin")
    g.parse_file()
