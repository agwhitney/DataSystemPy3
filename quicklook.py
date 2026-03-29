# Copied readers for now because things there are still coupled to tables
from datetime import datetime
import time
import struct
import matplotlib.pyplot as plt
from math import log, nan


class L0aReader:
    def __init__(self, filename):
        self.line_count = 0
        self.package_count = 0
        self.runtime = 0

        self.package_flag : bytes
        self.time_flag = b'TIME:'
        self.data_flag = b'DATA:'
        self.stop_flag = b':ENDS\n'

        self.filename = filename

        self.data = []



    def parse_file(self, line_limit=10_000):
        start = time.time()
        file = open(self.filename, 'rb')
        print(file.readline().decode())  # welcome line
        
        remainder = b''
        for line in file:
            self.line_count += 1
            if self.line_count == line_limit:
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
                    self.package_count += 1
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
                    self.package_count += 1

            data = remainder + data
            remainder = self.process_data(package_number, timestamp, data)
        file.close()
        self.runtime = time.time() - start


    def process_data(self, package_number, timestamp, data) -> bytes:
        raise NotImplementedError
    

    def quicklook(self):
        raise NotImplementedError


    def store_data(self, data: dict):
        row = list(data.values())
        self.data.append(row)


    def summary(self) -> str:
        return f"--{self} parse results: {self.package_count} packages out of {self.line_count} read lines. Elapsed time: {self.runtime:.1f} seconds."
            

class GPSReader(L0aReader):
    def __init__(self, filename):
        super().__init__(filename)
        self.package_flag = b'PACG:'

    def __str__(self):
        return "GPS Parser"


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
    

    def quicklook(self):
        time = []
        gpstime = []
        coords = []
        for row in self.data:
            time.append(row[1])
            gpstime.append(row[4])
            coords.append(row[2])

        fig, ax = plt.subplots()
        ax.plot(time, gpstime)
        ax.set(title="System time vs GPS time", xlabel='System', ylabel='GPS')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        x, y, z = zip(*coords)
        ax.scatter(x, y, z)
        ax.set(title="GPS position coordinates", xlabel="Latitude", ylabel="Longitude", zlabel="Elevation")

        plt.show()



class ThermistorReader(L0aReader):
    """
    DATA are voltages from each thermistor separated by '+'.
    1.12 V indicates an open circuit. 0.001 V indicates no connection.
    See config/thermistors.csv for a map of thermistor numbers to locations.
    """
    THERMISTOR_TOTAL = 40

    def __init__(self, filename):
        super().__init__(filename)
        self.package_flag = b'PACT:'

    
    def __str__(self):
        return "Thermistors Parser"


    def process_data(self, package_number, timestamp, data):
            voltages = [float(i) for i in data.decode().split('+')[1:]]  # Data starts with '+' creating empty entry

            voltages += [0.001] * (self.THERMISTOR_TOTAL - len(voltages))  # Fills count to 40 if there are fewer connected/reading.
            row = {'Packagenumber': package_number, 'Timestamp': timestamp, 'Voltages': voltages}
            self.store_data(row)
            return b''
    

    def quicklook(self):
        def kelvin(volt):
            r = 5000 * (volt / (1.12 - volt))
            try:
                temp = 1 / (1.29e-3 + 2.34e-4*log(r) + 1.10e-7*log(r)**3 + -6.51e-11*log(r)**5)
            except ValueError as e:
                temp = nan
            return temp
        
        time = []
        temps = []
        for row in self.data:
            time.append(row[1])
            temps.append(list(map(kelvin, row[2])))

        fig, ax = plt.subplots()
        ax.plot(time, temps)
        ax.set(
            title="Thermistors", xlabel="Time (s)", ylabel="Temperature (K)",
            ylim=(280, 350)
        )
        plt.show()



class RadiometerReader(L0aReader):
    def __init__(self, filename):
        super().__init__(filename)
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
    def get_radiometer_row(package_number: int, timestamp: float, values: bytes, i: int) -> dict:
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
                values = struct.unpack('>9HB', data[index:indexend])
                row = self.get_radiometer_row(package_number, timestamp, values, i=8)
                index = indexend

                self.store_data(row)
                self.n_AMR += 1

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
    

    def quicklook(self):
        time = []
        counts = []
        motor = []
        for row in self.data:
            if row[2] == 0:
                time.append(row[0])
                counts.append(row[1])
                motor.append(row[5])

        fig, ax = plt.subplots()
        ax.plot(time, counts)
        ax.set(title="Radiometer counts", xlabel="Time", ylabel="Counts")

        fig, ax = plt.subplots()
        ax.plot(time, motor)
        ax.set(title="Motor position", xlabel="Time", ylabel="Position")

        plt.show()





if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:
        raise IndexError("Provide binary filename as argument.")
    
    filename = sys.argv[1]
    if filename.find("Radiometer") != -1:
        reader = RadiometerReader(filename)
    elif filename.find("GPS-IMU") != -1:
        reader = GPSReader(filename)
    elif filename.find("Thermistors") != -1:
        reader = ThermistorReader(filename)
    else:
        raise ValueError("Provided file not found or incorrect.")

    reader.parse_file()
    reader.quicklook()