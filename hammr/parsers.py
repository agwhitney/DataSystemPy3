"""
Classes for taking the binary data (Level 0a) recorded by HAMMR-HD and parsing it into an
organized HDF5 file format (Level 0b).
Data after the first line (a welcome message) is recorded in binary with the following format:
PAC{char}:{int}TIME:{float}DATA:{bytes}:ENDS
"""
from datetime import datetime
import time
import struct


class Parser:
    """
    Reads the raw data (L0a) and, in the instrument subclasses, populates .h5 tables (L0b).
    """
    line_count = 0


    def __init__(self, filename: str, verbose: bool):
        self.filename = filename
        self.verbose = verbose

        self.package_flag : bytes  # Initialized per instrument
        self.time_flag = b'TIME:'
        self.data_flag = b'DATA:'
        self.stop_flag = b':ENDS\n'  # Suggested to not rely on `\n`, but it seems fine

        self.package_count = 0
        self.runtime = 0
        
        # Unused?
        # self.to_plot = np.array([])
        # self.data_len = np.array([])

    
    def parse_data(self, timestamp, data, package_number):
        raise NotImplementedError("Implement in subclass!")
    

    def summary(self) -> str:
        return f"--{self} parse results: {self.package_count} packages out of {self.line_count} read lines. Elapsed time: {self.runtime} seconds."
    

    def iterative_parsing(self):
        """
        Goes line by line through data files and passes data to Parser.parse_h5().
        This method is timed, and the result set to `self.runtime`.
        """
        with open(self.filename, 'rb') as f:
            start = time.time()
            welcome = f.readline()
            print(welcome.decode())

            # Loop line by line
            while True:
                line = f.readline()
                if not line:
                    break
                Parser.line_count += 1

                # Extract data from line or lines, between DATA and END flags.
                if line.startswith(self.package_flag):
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
                    elif not line.endswith(self.stop_flag):
                        data = b''
                        data += line[line.index(self.data_flag) + len(self.data_flag) : ]
                        continue
                
                elif not line.startswith(self.package_flag):
                    # Middle of split line
                    if not line.endswith(self.stop_flag):
                        data += line
                        continue
                    
                    # End of split line
                    elif line.endswith(self.stop_flag):
                        data += line[ : -len(self.stop_flag)]

                # Send complete data line to parsing method
                # self.to_plot = np.append(self.to_plot, package_number)
                # self.data_len = np.append(self.data_len, len(data))
                self.parse_data(timestamp, data, package_number)
                self.package_count += 1
        
        end = time.time()
        self.runtime = int(end - start)
        return


class RadiometerParser(Parser):
    def __str__(self):
        return "Radiometer Parser"


    def __init__(self, filename, sampleACT, sampleAMR, sampleSND, verbose):
        super().__init__(filename, verbose)
        self.package_flag = b'PACR:'
        self.row_pointer_AMR = sampleAMR
        self.row_pointer_ACT = sampleACT
        self.row_pointer_SND = sampleSND

        # counters - x is just the number of processed rows
        self.x_AMR = 0
        self.x_ACT = 0
        self.x_SND = 0
        self.errorR = 0

        # Channel data is prefixed by a three-peat of the same header value
        self.MW_HEADER  = [85, 85, 85]
        self.MMW_HEADER = [87, 87, 87]
        self.SND_HEADER = [93, 93, 93]

        self.bytes_per_datagram = {'AMR': 22, 'ACT': 14, 'SND': 38}

        # Start parsing
        self.iterative_parsing()


    @staticmethod
    def fill_row(row, timestamp, values, package_number, i) -> None:
        motor_firstPart = values[i] % 64
        
        row['Timestamp'] = timestamp
        row['Counts'] = values[:i]
        row['SystemStatus'] = int((values[i] // 64) % 32)
        row['NewSequence'] = int((values[i] // 2048) % 4)
        row['Id'] = int(values[i] // 16384)
        row['MotorPosition'] = motor_firstPart * 256 + values[i+1]
        # row['Packagenumber'] = package_number  # TODO this fails for long files if package_number > 65536 (check type in datastructures.py). # Was not included in py2



    def parse_data(self, timestamp, data, package_number):
        """
        Crawls through `data` to find the header for the respective channel, then processes the datagram accordingly.
        Once it finds a datagram, the next header is found from the last 3 bytes (i.e., it overlaps).
        """
        header = [0, 0, 0]
        index = 0
        bytes_remaining = len(data)

        while bytes_remaining > max(self.bytes_per_datagram.values()):
            if header == self.MW_HEADER:
                indexstart = index
                indexend = index + self.bytes_per_datagram['AMR']
                values = struct.unpack('>9H4B', data[indexstart:indexend])
                index = indexend

                self.fill_row(self.row_pointer_AMR, timestamp, values, package_number, i=8)
                self.row_pointer_AMR.append()
                header = list(values[-3:])
                self.x_AMR += 1

                if self.verbose is True:
                    print(f"AMR: Line {self.x_AMR} -- {values}")

            elif header == self.MMW_HEADER:
                indexstart = index
                indexend = index + self.bytes_per_datagram['ACT']
                values = struct.unpack('>5H4B', data[indexstart:indexend])
                index = indexend

                self.fill_row(self.row_pointer_ACT, timestamp, values, package_number, i=4)
                self.row_pointer_ACT.append()
                header = list(values[-3:])
                self.x_ACT += 1

                if self.verbose:
                    print(f"ACT: Line {self.x_ACT} -- {values}")

            elif header == self.SND_HEADER:
                indexstart = index
                indexend = index + self.bytes_per_datagram['SND']
                values = struct.unpack('>17H4B', data[indexstart:indexend])
                index = indexend

                self.fill_row(self.row_pointer_SND, timestamp, values, package_number, i=16)
                self.row_pointer_SND.append()
                header = list(values[-3:])
                self.x_SND += 1

                if self.verbose:
                    print(f"SND: Line {self.x_SND} -- {values}")

            else:
                if index > max(self.bytes_per_datagram.values()):  # Crawl exceeded what should have been the longest datagram without finding one
                    self.errorR += 1
                    print("-------------------------------------------------")
                    print("Parsing ERROR -> INDEX:", index, "Header:", header,
                          "Counts - SND:", self.x_SND, "AMR:", self.x_AMR, "ACT:", self.x_ACT,
                          "- ERROR #", self.errorR)
                    print("-------------------------------------------------")
                    
                else:  # Crawling...
                    if self.verbose:
                        print("-------------------------------------------------")
                        print("Synchronizing a new line -> INDEX:", index, "Header:", header,
                              "SND:", self.x_SND, "AMR:", self.x_AMR, "ACT:", self.x_ACT)
                        print("-------------------------------------------------")

                # Update header by incrementing
                header[0] = header[1]
                header[1] = header[2]
                indexstart = index
                indexend = index + 1
                header[2] = struct.unpack('>1B', data[indexstart:indexend])[0]
                index = indexend

            bytes_remaining = len(data) - index

        # Return unprocessed bytes (not used - other parsers return None)
        b = struct.pack('3b', *header)
        vals = b + data[-bytes_remaining:]
        return vals
    

class ThermistorParser(Parser):
    """
    DATA are voltages from each thermistor separated by '+'.
    1.12 V indicates an open circuit. 0.001 V indicates no connection.
    See config/thermistors.csv for a map of thermistor numbers to locations.
    """
    THERMISTOR_TOTAL = 40

    def __str__(self):
        return "Thermistor Parser"
    
    def __init__(self, filename, sampleTHM, verbose):
            super().__init__(filename, verbose)
            self.package_flag = b'PACT:'
            self.row_pointer = sampleTHM

            # Start parsing
            self.iterative_parsing()


    def parse_data(self, timestamp, data, package_number):
            voltages = [float(i) for i in data.decode().split('+')[1:]]  # Starts with '+' creating empty entry
            if self.verbose:
                print(f"-> {time.strftime("%b-%d-%Y -- %H:%M:%S", time.localtime(int(timestamp)))} -> {package_number} -> {voltages}")
            connected = len(voltages)
            self.row_pointer['Timestamp'] = timestamp
            # self.row_pointer['Packagenumber'] = package_number
            self.row_pointer['Voltages'] = voltages + [0.001] * (self.THERMISTOR_TOTAL - connected) # This line fills to 40 Thermistors in case there are fewer plugged in into the system! Do not delete it!, XB
            self.row_pointer.append()


class GPSParser(Parser):
    def __str__(self):
        return "GPS-IMU Parser"
    
    def __init__(self, filename, sampleIMU, verbose):
        super().__init__(filename, verbose)
        self.package_flag = b'PACG:'
        self.row_pointer = sampleIMU

        # Start parsing immediately
        self.iterative_parsing()


    def parse_data(self, timestamp, data, package_number):
        """
        The recorded data is a frame from the GPS with the delimiter already trimmed.
        The delimiter was chosen to be the frame end and prefix, see the OEM documentation and instruments.py.
        This leaves the data (46 bytes) plus 2 extra variable bytes from the suffix (CRC16).
        3x float - 3x double - 6x byte 1x uInt - 2x byte
        roll-pitch-yaw lat-lon-alt time crc16
        """
        if len(data) == 48:
            vals = struct.unpack('>fffdddBBBBBBI', data[:46])  # 13 values

            self.row_pointer['EulerAngles'] = vals[:3]
            self.row_pointer['Position'] = vals[3:6]
            
            d = datetime(vals[6] + 2000, vals[7], vals[8], vals[9], vals[10], vals[11])
            # XB For testing purposes only, GPS/IMU does only provide time and position if it is receiving GPS satellites
            self.row_pointer['GPSTime'] = time.mktime(d.timetuple())
            self.row_pointer['Timestamp'] = timestamp
            # self.row_pointer['Packagenumber'] = package_number
            self.row_pointer.append()
        
        else:
            print(f"GPS data is {len(data)} bytes and should be 48. Skipping this line (instrumentparsers.py).")
            