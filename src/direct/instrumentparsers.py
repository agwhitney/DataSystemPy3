"""
py2 ParserAux.py
"""
import numpy as np
import struct
from datetime import datetime


class BasicParser:
    PackageHeader = ''
    TimeHeader = 'TIME'
    DataHeader = 'DATA:'
    EndHeader = ':ENDS'
    verbose = True
    package = 0
    nReadlines = 0
    toplot = []
    datalength = [] 
    sampleAMR = ''
    sampleACT = ''
    sampleSND = ''


    def actualh5parser(self, timestamp, input_vals, package_number):
        # This method is here just for ilustation, it should be overriden by each instance of the class
        print ("Warning: This method has not been overriden properly!")


    def IterativeParsing(self,fileDescription):
        self.toplot = np.array([])
        self.datalength = np.array([])
        to5hparser = np.array([])
        leftvalues = ''
        iterData = []
        isCompleteLine = True
        welcome = fileDescription.readline()
        print(welcome)
        
        # "The following part of the script reads lines from a structured data file and detects 
        # if a line is complete or not"
        for line in fileDescription.readlines():
            self.nReadLines += 1
            print(line)
            
            if isCompleteLine:
                iterData = ''
                a = line.index(self.PackageHeader)
                b = line.index(self.TimeHeader)
                c = line.index(self.DataHeader)
                d = len(line)
                
                package_number = int(''.join(line[a+5:b]))
                timestamp = float(''.join(line[b+5:c]))
        
                #The line is not complete
                if line[-6:-1] != self.EndHeader:
                    isCompleteLine = False
                    print(f"TRUE -> {isCompleteLine} {line[-6:-1]} -> {self.EndHeader} HEADER -> {line[:5]}")
                    iterData = line[c+5:]
        
                else:
                    isCompleteLine = True
                    print (f"TRUE -> {isCompleteLine} {line[-6:-1]} -> {self.EndHeader} HEADER-> {line[:5]}")
                    iterData = line[c+5:-6]
                    datapackagelength = len(iterData)
                    print(self.package,'->', datetime.strftime("%b-%d-%Y -- %H:%M:%S",datetime.localtime(int(timestamp))), '->', package_number, 'DATA LENGTH:', datapackagelength)
                    self.toplot = np.append(self.toplot, package_number)
                    self.datalength = np.append(self.datalength, datapackagelength)
                    to5hparser = ''.join([leftvalues, iterData])
                    leftvalues = self.actualh5parser(timestamp, to5hparser, package_number)
                    self.package += 1
        
            elif isCompleteLine is False:
                # Line not complete yet
                if line[-6:-1] != self.EndHeader:
                    isCompleteLine = False
                    print(f"FALSE -> {isCompleteLine} {line[-6:-1]} -> {self.EndHeader} HEADER -> {line[:5]}")
                    iterData += line
        
                # Line complete
                else:
                    isCompleteLine = True
                    print(f"FALSE -> {isCompleteLine} {line[-6:-1]} -> {self.EndHeader} HEADER -> {line[:5]}")
                    iterData += line[:-6]
                    datapackagelength = len(iterData)
                    print (self.package,'->', datetime.strftime("%b-%d-%Y -- %H:%M:%S",datetime.localtime(int(timestamp))), '->', package_number, 'DATA LENGTH:', datapackagelength)
                    self.toplot = np.append(self.toplot, package_number)
                    self.datalength = np.append(self.datalength, datapackagelength)
                    to5hparser = ''.join([leftvalues, iterData])
                    leftvalues = self.actualh5parser(timestamp,to5hparser,package_number)
                    self.package += 1 
                    if self.package == 2:
                            break           
        fileDescription.close()

 
class RadiometerParser(BasicParser):
    def __init__(self, filedescription, sampleACT, sampleAMR, sampleSND, verbose):
        self.package_number = 'PACR'
        self.sampleAMR = sampleAMR
        self.sampleACT = sampleACT
        self.sampleSND = sampleSND

        self.x_AMR = 0
        self.x_ACT = 0
        self.x_SND = 0
        self.errorR = 0
        self.verbose = verbose  

        MW_HEADER = 'MWR'
        MMW_HEADER = 'MMW'
        SND_HEADER = 'SND'

        self.MW_HEADERARRAY = [MW_HEADER, MW_HEADER, MW_HEADER]
        self.MMW_HEADERARRAY = [MMW_HEADER, MMW_HEADER, MMW_HEADER]
        self.SND_HEADERARRAY = [SND_HEADER, SND_HEADER, SND_HEADER]

        self.bytePerDattagram_AMR = 22
        self.bytePerDattagram_ACT = 14
        self.bytePerDattagram_SND = 38

        #Parsing
        self.IterativeParsing(filedescription)


    def actualh5parser(self, timestamp, inputvalues, PackageNumber):
        header = [0, 0, 0]
        index = 0
        leftvalues = len(inputvalues)

        while leftvalues > self.bytesPerDatagram_SND:
            Value = {}

            if header == self.MW_HEADERARRAY:
                print('reading MW package', self.x_AMR, 'header: ', struct.unpack('>1B', self.c), struct.unpack('>1B', self.b), struct.unpack('>1B', self.a))
                indexstart = index
                indexend = index + self.bytesPerDatagram_ARM
                Value = struct.unpack('>9H4B', inputvalues[indexstart:indexend])
                index = indexend

                self.sampleAMR['Timestamp'] = timestamp
                self.sampleAMR['Counts'] = Value[:8]
                MotorFirstPart = Value[8] % 64
                self.sampleAMR['SytemStatus'] = int((Value[8] // 64) % 32)
                self.sampleAMR['NewSequence'] = int((Value[8] // 2048) % 4)
                self.sampleAMR['Id'] = int(Value[8] // 16384)
                self.sampleAMR['MotorPosition'] = MotorFirstPart * 256 + Value[9]
                self.sampleAMR.append()
                header = list(Value[10:13])
                self.x_AMR += 1

                if self.verbose is True:
                    print('AMR:', self.x_AMR, header[0], header[1], header[2], Value)

            elif header == self.MMW_HEADERARRAY:
                indexstart = index
                indexend = index + self.bytesPerDatagram_ACT
                Value = struct.unpack('>5H4B', inputvalues[indexstart:indexend])
                index = indexend

                self.sampleACT['Timestamp'] = timestamp
                self.sampleACT['Counts'] = Value[:4]
                MotorFirstPart = Value[4] % 64
                self.sampleACT['SytemStatus'] = int((Value[4] // 64) % 32)
                self.sampleACT['NewSequence'] = int((Value[4] // 2048) % 4)
                self.sampleACT['Id'] = int(Value[4] // 16384)
                self.sampleACT['MotorPosition'] = MotorFirstPart * 256 + Value[5]
                self.sampleACT.append()
                header = list(Value[6:9])
                self.x_ACT += 1

                if self.verbose:
                    print('ACT:', self.x_ACT, header[0], header[1], header[2], Value)

            elif header == self.SND_HEADERARRAY:
                print ('reading MW package', self.x_AMR, 'header: ', struct.unpack('>1B', self.c), struct.unpack('>1B', self.b), struct.unpack('>1B', self.a))
                indexstart = index
                indexend = index + self.bytesPerDatagram_SND
                Value = struct.unpack('>17H4B', inputvalues[indexstart:indexend])
                index = indexend

                self.sampleSND['Timestamp'] = timestamp
                self.sampleSND['Counts'] = Value[:16]
                MotorFirstPart = Value[16] % 64
                self.sampleSND['SytemStatus'] = int((Value[16] // 64) % 32)
                self.sampleSND['NewSequence'] = int((Value[16] // 2048) % 4)
                self.sampleSND['Id'] = int(Value[16] // 16384)
                self.sampleSND['MotorPosition'] = MotorFirstPart * 256 + Value[17]
                self.sampleSND.append()
                header = list(Value[18:21])
                self.x_SND += 1
                #add print() if needed, SF

                if self.verbose:
                    print('SND:', self.x_SND, header[0], header[1], header[2], Value)

            else:
                if index > self.bytesPerDatagram_SND:
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
                header[2] = struct.unpack('>1B', inputvalues[indexstart:indexend])[0]
                index = indexend

            leftvalues = len(inputvalues) - index

        # Return unprocessed bytes
        b = bytes()
        b = b.join((struct.pack('b', h) for h in header))
        valuestoretorn = b + inputvalues[-leftvalues:]
        return valuestoretorn
    

class ThermistorParser(BasicParser):
    def __init__(self, fileDescription, sampleTHR, verbose):
            self.PackageHeader = 'PACT:'
            self.sampleTHR = sampleTHR
            self.verbose = verbose
            # Start parsing
            self.IterativeParsing(fileDescription)


    def actualh5parser(self, timestamp, inputvalues, PackageNumber):
            iterData = iter(str(inputvalues).split('+'))
            dumpit = next(iterData)
            Data = [float(e) for e in iterData]
            if self.verbose:
                print('->', datetime.strftime("%b-%d-%Y -- %H:%M:%S", datetime.localtime(int(timestamp))),
                '->', PackageNumber, '->', repr(Data))
            NumberOfThermistors = len(Data)
            self.sampleTHR['Timestamp'] = timestamp
            self.sampleTHR['Packagenumber'] = PackageNumber
            self.sampleTHR['Voltages'] = Data + [0.001] * (40 - NumberOfThermistors) # This line completes up to 40 Thermistors in case there are less pluged in into the system! Do not delete it!, XB
            self.sampleTHR.append()
            leftvalues = ''
            return leftvalues  # No remaining data to return


class GPSParser(BasicParser):
    def __init__(self, fileDescription, sampleIMU, verbose):
        self.PackageHeader = 'PACG:'
        self.sampleIMU = sampleIMU
        self.verbose = verbose

        # Start parsing immediately
        self.IterativeParsing(fileDescription)


    def actualh5parser(self, timestamp, inputvalues, PackageNumber):
        if len(inputvalues) == 48:
            Value = struct.unpack('>fffdddBBBBBBI', inputvalues[0:46])

            self.sampleIMU['EulerAngles'] = Value[:3]
            self.sampleIMU['Position'] = Value[3:6]
            print (repr(Value[6:13]))
            
            d = datetime(Value[6] + 2000, Value[7], Value[8], Value[9], Value[10], Value[11])
            ## For testing purposes only, GPS/IMU does only provide time and position if it is receiving GPS satellites, XB
            self.sampleIMU['GPSTime'] = datetime.mktime(d.timetuple())
            self.sampleIMU['Timestamp'] = timestamp
            self.sampleIMU['Packagenumber'] = PackageNumber
            self.sampleIMU.append()
            leftvalues = ''
            return leftvalues


