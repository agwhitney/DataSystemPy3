from datetime import datetime
import time
import struct


class L0aReader:
    def __init__(self, filename, table):
        self.line_count = 0
        self.package_flag : bytes
        self.time_flag = b'TIME:'
        self.data_flag = b'DATA:'
        self.stop_flag = b':ENDS\n'

        self.filename = filename
        self.table = table


    def parse_file(self, line_limit=0):
        file = open(self.filename, 'rb')
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
        file.close()


    def process_data(self, package_number, timestamp, data) -> bytes:
        print(package_number, timestamp, data)
        return b''


    def store_data(self, data: dict):
        for key, val in data.items():
            self.table.row[key] = val
        self.table.row.append()
            

class GPSReader(L0aReader):
    def __init__(self, filename, table):
        super().__init__(filename, table)
        self.package_flag = b'PACG:'


    def process_data(self, package_number, timestamp, data) -> bytes:
        """
        The recorded data is a frame from the GPS with the delimiter already trimmed.
        The delimiter was chosen to be the frame end and prefix, see the OEM documentation and instruments.py.
        This leaves the data (46 bytes) plus 2 extra variable bytes from the suffix (CRC16).
        3x float - 3x double - 6x byte 1x uInt - 2x byte
        roll-pitch-yaw lat-lon-alt time crc16
        """
        if not len(data) == 48:
            print(f"GPS data is {len(data)} bytes and should be 48. Skipping this line (instrumentparsers.py).")
            return b''
        
        vals = struct.unpack('>fffdddBBBBBBI', data[:46])  # 13 values
        euler_angles = vals[:3]
        position = vals[3:6]
        d = datetime(vals[6] + 2000, vals[7], vals[8], vals[9], vals[10], vals[11])
        gps_timestamp = time.mktime(d.timetuple())

        row = {'Packagenumber': package_number, 'Timestamp': timestamp, 'EulerAngles': euler_angles, 'Position': position, 'GPSTime': gps_timestamp}
        self.store_data(row)
        return b''


class ThermistorReader(L0aReader):
    """
    DATA are voltages from each thermistor separated by '+'.
    1.12 V indicates an open circuit. 0.001 V indicates no connection.
    See config/thermistors.csv for a map of thermistor numbers to locations.
    """
    THERMISTOR_TOTAL = 40

    def __init__(self, filename, table):
        super().__init__(filename, table)
        self.package_flag = b'PACT:'


    def process_data(self, package_number, timestamp, data):
            voltages = [float(i) for i in data.decode().split('+')[1:]]  # Data starts with '+' creating empty entry

            voltages += [0.001] * (self.THERMISTOR_TOTAL - len(voltages))  # Fills count to 40 if there are fewer connected/reading.
            row = {'Packagenumber': package_number, 'Timestamp': timestamp, 'Voltages': voltages}
            self.store_data(row)
            return b''
            

class RadiometerReader(L0aReader):
    def __init__(self, filename, table):
        super().__init__(filename, table)
        self.package_flag = b'PACR:'

        # counters - x is just the number of processed rows
        self.n_AMR = 0
        self.n_ACT = 0
        self.n_SND = 0
        self.errorR = 0

        # Channel data is prefixed by a three-peat of the same header value
        self.MW_HEADER  = [85, 85, 85]
        self.MMW_HEADER = [87, 87, 87]
        self.SND_HEADER = [93, 93, 93]

        self.bytes_per_datagram = {'AMR': 22, 'ACT': 14, 'SND': 38}


    def __str__(self):
        return "Radiometer Parser"


    @staticmethod
    def get_radiometer_row(package_number, timestamp, values, i) -> dict:
        row = {}
        row['Timestamp'] = timestamp
        row['Counts'] = values[:i]
        row['SystemStatus'] = int((values[i] // 64) % 32)
        row['NewSequence'] = int((values[i] // 2048) % 4)
        row['Id'] = int(values[i] // 16384)
        row['MotorPosition'] = (values[i] % 64) * 256 + values[i+1]
        # row['Packagenumber'] = package_number  # TODO this fails for long files if package_number > 65536 (check type in datastructures.py). # Was not included in py2
        return row


    def process_data(self, package_number, timestamp, data) -> bytes:
        """
        Crawls through `data` to find the header for the respective channel, then processes the datagram accordingly.
        Once it finds a datagram, the next header is found from the last 3 bytes (i.e., it overlaps).
        Returns a remainder of bytes, which would be continued in the next data package.
        """
        index = 0
        bytes_remaining = len(data)

        while bytes_remaining > max(self.bytes_per_datagram.values()):
            header = list(struct.unpack('3B', data[index: index+3]))
            index += 3

            if header == self.MW_HEADER:
                indexend = index + self.bytes_per_datagram['AMR'] - 3
                vals = struct.unpack('>9HB', data[index:indexend])
                row = self.get_radiometer_row(package_number, timestamp, vals, i=8)
                index = indexend

                self.store_data(row)
                self.n_AMR += 1

            # elif header == self.MMW_HEADER:
            #     indexstart = index
            #     indexend = index + self.bytes_per_datagram['ACT']
            #     values = struct.unpack('>5H4B', data[indexstart:indexend])
            #     index = indexend

            #     self.fill_row(self.row_pointer_ACT, timestamp, values, package_number, i=4)
            #     self.row_pointer_ACT.append()
            #     header = list(values[-3:])
            #     self.n_ACT += 1

            #     if self.verbose:
            #         print(f"ACT: Line {self.n_ACT} -- {values}")

            # elif header == self.SND_HEADER:
            #     indexstart = index
            #     indexend = index + self.bytes_per_datagram['SND']
            #     values = struct.unpack('>17H4B', data[indexstart:indexend])
            #     index = indexend

            #     self.fill_row(self.row_pointer_SND, timestamp, values, package_number, i=16)
            #     self.row_pointer_SND.append()
            #     header = list(values[-3:])
            #     self.n_SND += 1

            #     if self.verbose:
            #         print(f"SND: Line {self.n_SND} -- {values}")

            else:
                if index > max(self.bytes_per_datagram.values()):  # Crawl exceeded what should have been the longest datagram without finding one
                    self.errorR += 1
                    print("-------------------------------------------------")
                    print("Parsing ERROR -> INDEX:", index, "Header:", header,
                          "Counts - SND:", self.n_SND, "AMR:", self.n_AMR, "ACT:", self.n_ACT,
                          "- ERROR #", self.errorR)
                    print("-------------------------------------------------")
                # Update header by incrementing
                header[0] = header[1]
                header[1] = header[2]
                header[2] = struct.unpack('>1B', data[index:index+1])[0]
                index += 1

            bytes_remaining = len(data) - index
        # Return unprocessed bytes
        remainder = data[-bytes_remaining:]
        return remainder





if __name__ == '__main__':
    from datastructures import DataFile
    df = DataFile('./test.h5')

    g = GPSReader(
        r"C:\Users\agwhi\Desktop\260206_kba\data\26_02_06__14_09_14__1of6_260206_kba_tarmac10ms_GPS-IMU.bin",
        df.tables['IMU']
    )
    r = RadiometerReader(
        r"C:\Users\agwhi\Desktop\260206_kba\data\26_02_06__14_09_14__1of6_260206_kba_tarmac10ms_Radiometer.bin",
        df.tables['AMR']
    )
    t = ThermistorReader(
        r"C:\Users\agwhi\Desktop\260206_kba\data\26_02_06__14_09_14__1of6_260206_kba_tarmac10ms_Thermistors.bin",
        df.tables['THM']
    )
    g.parse_file()
    r.parse_file()
    t.parse_file()
