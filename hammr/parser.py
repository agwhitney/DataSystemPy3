import numpy as np


class Parser:
    """
    Reads the raw data (L0a) and, in the instrument subclasses, populates .h5 tables (L0b).
    """
    line_count = 0
    time_flag = b'TIME:'
    data_flag = b'DATA:'
    stop_flag = b':ENDS'


    def __init__(self, package_flag: bytes):
        self.package_flag = package_flag
        self.package_count = 0

        self.to_plot = np.array([])
        self.data_len = np.array([])

    
    def parse_h5(self):
        raise NotImplementedError(f"Implement in subclass!")
    

    def iterative_parsing(self, binfile):
        # Indices for splitting flags from data
        data_start = line.index(self.data_flag) + len(self.data_flag)
        data_end = -len(self.stop_flag)
        pack_start = line.index(self.package_flag) + len(self.package_flag)
        time_start = line.index(self.time_flag) + len(self.time_flag)

        welcome = binfile.readline()
        print(welcome.decode())

        while True:
            line = binfile.readline()
            if not line:
                break
            Parser.line_count += 1

            if line.startswith(self.package_flag):
                package_number = int(line[pack_start : line.index(self.time_flag)])
                timestamp = float(line[time_start : line.index(self.data_flag)])

                # Complete line
                if line.endswith(self.stop_flag):
                    data = line[data_start:data_end]

                # Start of split line
                elif not line.endswith(self.stop_flag):
                    data = b''
                    data += line[data_start:]
                    continue
            
            elif not line.startswith(self.package_flag):
                # Middle of split line
                if not line.endswith(self.stop_flag):
                    data += line
                    continue
                
                # End of split line
                elif line.endswith(self.stop_flag):
                    data += line[:data_end]

            # Send complete data line along
            self.to_plot = np.append(self.to_plot, package_number)
            self.data_len = np.append(self.data_len, len(data))
            print("goto parsing method") #self.parse_h5(timestamp, data, package_number)
            self.package_count += 1
        
        binfile.close()



            