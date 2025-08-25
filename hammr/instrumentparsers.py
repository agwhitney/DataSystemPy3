"""
py2 ParserAux.py
Parsing methods associated with each instrument. Each instrument runs iterative_parsing() defined in the BasicParser class,
which runs with the relevant parse_h5() method.
"""
import numpy as np
import struct
import time
from datetime import datetime


class BasicParser:
    package_header : bytes
    time_header = b'TIME'
    data_header = b'DATA:'
    end_header = b':ENDS'
    verbose = True
    package = 0
    toplot = []
    datalength = [] 
    sampleAMR = ''
    sampleACT = ''
    sampleSND = ''
    read_lines = 0


    def parse_h5(self, timestamp, input_vals, package_number):
        # This method is here just for illustration, it should be overriden by each instance of the class
        print("Warning: This method has not been overriden properly!")


    def iterative_parsing(self, fileDescription):
        self.toplot = np.array([])
        self.datalength = np.array([])
        to5hparser = np.array([])
        left_vals = ''
        iterData = []
        isCompleteLine = True

        welcome = fileDescription.readline()
        print(welcome.decode())
        
        # Reads lines from a structured data file and detects if a line is complete or not
        for line in fileDescription.readlines():
            BasicParser.read_lines += 1
            
            if isCompleteLine:
                iterData = ''
                a = line.index(self.package_header)
                b = line.index(self.time_header)
                c = line.index(self.data_header)
                
                package_number = int(line[a+5:b])
                timestamp = float(line[b+5:c])
        
                # The line is not complete
                if line[-6:-1] != self.end_header:
                    isCompleteLine = False
                    # print(f"TRUE -> {isCompleteLine} {line[-6:-1]} -> {self.end_header} HEADER -> {line[:5]}")
                    iterData = line[c+5:]
        
                else:
                    isCompleteLine = True
                    # print (f"TRUE -> {isCompleteLine} {line[-6:-1]} -> {self.end_header} HEADER-> {line[:5]}")
                    iterData = line[c+5:-6]
                    # print(self.package,'->', time.strftime("%b-%d-%Y -- %H:%M:%S", time.localtime(int(timestamp))), '->', package_number, 'DATA LENGTH:', len(iterData))
                    self.toplot = np.append(self.toplot, package_number)
                    self.datalength = np.append(self.datalength, len(iterData))
                    to5hparser = iterData
                    left_vals = self.parse_h5(timestamp, to5hparser, package_number)
                    self.package += 1
        
            elif not isCompleteLine:
                # Line not complete yet
                if line[-6:-1] != self.end_header:
                    isCompleteLine = False
                    # print(f"FALSE -> {isCompleteLine} {line[-6:-1]} -> {self.end_header} HEADER -> {line[:5]}")
                    iterData += line
        
                # Line complete
                else:
                    isCompleteLine = True
                    iterData += line[:-6]
                    # print (self.package,'->', time.strftime("%b-%d-%Y -- %H:%M:%S", time.localtime(int(timestamp))), '->', package_number, 'DATA LENGTH:', len(iterData))
                    self.toplot = np.append(self.toplot, package_number)
                    self.datalength = np.append(self.datalength, len(iterData))
                    to5hparser = iterData
                    left_vals = self.parse_h5(timestamp, to5hparser, package_number)
                    self.package += 1
     
        fileDescription.close()

 
class RadiometerParser(BasicParser):
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
                print('reading MW package', self.x_AMR, 'header: ', struct.unpack('>1B', self.c), struct.unpack('>1B', self.b), struct.unpack('>1B', self.a))
                indexstart = index
                indexend = index + self.bytes_per_datagram['ARM']
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
    

class ThermistorParser(BasicParser):
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


class GPSParser(BasicParser):
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