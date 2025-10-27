from datetime import datetime
import numpy as np
import time
import struct


class Parser:
    """
    Reads the raw data (L0a) and, in the instrument subclasses, populates .h5 tables (L0b).
    """
    line_count = 0


    def __init__(self):
        self.package_flag : bytes  # Initialized per instrument
        self.time_flag = b'TIME:'
        self.data_flag = b'DATA:'
        self.stop_flag = b':ENDS'

        self.package_count = 0

        # Unused?
        self.to_plot = np.array([])
        self.data_len = np.array([])

    
    def parse_h5(self):
        raise NotImplementedError("Implement in subclass!")
    

    def iterative_parsing(self, binfile):
        """
        Goes line by line through data files and passes data to Parser.parse_h5().
        First line is a welcome message.
        Data lines are formatted as:
            PAC{char}:{int}TIME:{float}DATA:{bytes}:ENDS
        """
        welcome = binfile.readline()
        print(welcome.decode())

        # Loop line by line
        while True:
            line = binfile.readline()
            if not line:
                break
            Parser.line_count += 1

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
            self.to_plot = np.append(self.to_plot, package_number)
            self.data_len = np.append(self.data_len, len(data))
            self.parse_h5(timestamp, data, package_number)
            self.package_count += 1
        
        binfile.close()
        return


class RadiometerParser(Parser):
    def __init__(self, filedescription, sampleACT, sampleAMR, sampleSND, verbose):
        self.package_header = b'PACR:'
        self.sampleAMR = sampleAMR
        self.sampleACT = sampleACT
        self.sampleSND = sampleSND

        self.x_AMR = 0
        self.x_ACT = 0
        self.x_SND = 0
        self.errorR = 0
        self.verbose = verbose  

        MW_HEADER = 85  # 'MWR'
        MMW_HEADER = 87  # 'MMW'
        SND_HEADER = 93  #'SND'

        self.MW_HEADERARRAY = 3 * [MW_HEADER]  # list w/ 3 identical entries
        self.MMW_HEADERARRAY = 3 * [MMW_HEADER]
        self.SND_HEADERARRAY = 3 * [SND_HEADER]

        self.bytes_per_datagram = {'AMR': 22, 'ACT': 14, 'SND': 38}

        # Start parsing
        self.iterative_parsing(filedescription)


    @staticmethod
    def fill_row(row, timestamp, value, i) -> None:
        motor_firstPart = value[i] % 64
        
        row['Timestamp'] = timestamp
        row['Counts'] = value[:i]
        row['SystemStatus'] = int((value[i] // 64) % 32)
        row['NewSequence'] = int((value[i] // 2048) % 4)
        row['Id'] = int(value[i] // 16384)
        row['MotorPosition'] = motor_firstPart * 256 + value[i+1]



    def parse_h5(self, timestamp, input_vals, package_number):
        header = [0, 0, 0]
        index = 0
        left_vals = len(input_vals)

        while left_vals > self.bytes_per_datagram['SND']:
            if header == self.MW_HEADERARRAY:
                indexstart = index
                indexend = index + self.bytes_per_datagram['AMR']
                value = struct.unpack('>9H4B', input_vals[indexstart:indexend])
                index = indexend

                self.fill_row(self.sampleAMR, timestamp, value, i=8)
                self.sampleAMR.append()
                header = list(value[10:13])
                self.x_AMR += 1

                if self.verbose is True:
                    print('AMR:', self.x_AMR, header[0], header[1], header[2], value)

            elif header == self.MMW_HEADERARRAY:
                indexstart = index
                indexend = index + self.bytes_per_datagram['ACT']
                value = struct.unpack('>5H4B', input_vals[indexstart:indexend])
                index = indexend

                self.fill_row(self.sampleACT, timestamp, value, i=4)
                self.sampleACT.append()
                header = list(value[6:9])
                self.x_ACT += 1

                if self.verbose:
                    print('ACT:', self.x_ACT, header[0], header[1], header[2], value)

            elif header == self.SND_HEADERARRAY:
                print ('reading MW package', self.x_AMR, 'header: ', struct.unpack('>1B', self.c), struct.unpack('>1B', self.b), struct.unpack('>1B', self.a))
                indexstart = index
                indexend = index + self.bytes_per_datagram['SND']
                value = struct.unpack('>17H4B', input_vals[indexstart:indexend])
                index = indexend

                self.fill_row(self.sampleSND, timestamp, value, i=16)
                self.sampleSND.append()
                header = list(value[18:21])
                self.x_SND += 1

                if self.verbose:
                    print('SND:', self.x_SND, header[0], header[1], header[2], value)

            else:
                if index > self.bytes_per_datagram['SND']:
                    self.errorR += 1
                    print("-------------------------------------------------")
                    print("Parsing ERROR -> INDEX:", index, "Header:", header,
                          "SND:", self.x_SND, "AMR:", self.x_AMR, "ACT:", self.x_ACT,
                          "- ERROR #", self.errorR)
                    print("-------------------------------------------------")
                else:
                    if self.verbose:
                        print("-------------------------------------------------")
                        print("Synchronizing a new line -> INDEX:", index, "Header:", header,
                              "SND:", self.x_SND, "AMR:", self.x_AMR, "ACT:", self.x_ACT)
                        print("-------------------------------------------------")

                # Update header
                header[0] = header[1]
                header[1] = header[2]
                indexstart = index
                indexend = index + 1
                header[2] = struct.unpack('>1B', input_vals[indexstart:indexend])[0]
                index = indexend

            left_vals = len(input_vals) - index

        # Return unprocessed bytes
        b = bytes()
        b = b.join((struct.pack('b', h) for h in header))
        vals = b + input_vals[-left_vals:]
        return vals
    

class ThermistorParser(Parser):
    def __init__(self, fileDescription, sampleTHM, verbose):
            self.package_header = b'PACT:'
            self.sampleTHM = sampleTHM
            self.verbose = verbose

            # Start parsing
            self.iterative_parsing(fileDescription)


    def parse_h5(self, timestamp, input_vals, package_number):
            iterData = iter(input_vals.decode().split('+')[1:])
            data = [float(e) for e in iterData]
            if self.verbose:
                print(f"-> {time.strftime("%b-%d-%Y -- %H:%M:%S", time.localtime(int(timestamp)))} -> {package_number} -> {data}")
            thermistor_count = len(data)
            self.sampleTHM['Timestamp'] = timestamp
            self.sampleTHM['Packagenumber'] = package_number
            self.sampleTHM['Voltages'] = data + [0.001] * (40 - thermistor_count) # This line completes up to 40 Thermistors in case there are less pluged in into the system! Do not delete it!, XB
            self.sampleTHM.append()
            vals = ''
            return vals  # No remaining data to return


class GPSParser(Parser):
    def __init__(self, fileDescription, sampleIMU, verbose):
        self.package_header = b'PACG:'
        self.sampleIMU = sampleIMU
        self.verbose = verbose

        # Start parsing immediately
        self.iterative_parsing(fileDescription)


    def parse_h5(self, timestamp, data, package_number):
        """
        data is a frame from the GPS with the delimiter trimmed. The delimiter was chosen to be the frame end and prefix.
        This leaves the data (46 bytes) and two extra variable bytes from the suffix.
        I assume the data length should be a function of the GPS settings. See instruments.py.
        """
        if len(data) == 48:
            vals = struct.unpack('>fffdddBBBBBBI', data[:46])  # 13 values

            self.sampleIMU['EulerAngles'] = vals[:3]
            self.sampleIMU['Position'] = vals[3:6]
            
            d = datetime(vals[6] + 2000, vals[7], vals[8], vals[9], vals[10], vals[11])
            # XB For testing purposes only, GPS/IMU does only provide time and position if it is receiving GPS satellites
            self.sampleIMU['GPSTime'] = time.mktime(d.timetuple())
            self.sampleIMU['Timestamp'] = timestamp
            self.sampleIMU['Packagenumber'] = package_number
            self.sampleIMU.append()
            vals = ''
            return vals
        
        else:
            print(f"Frame is {len(data)} bytes. Skipping this line (instrumentparsers.py).")
            