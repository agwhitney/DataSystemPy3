"""
py2 ParserAux.py
"""

import tables as tb
import numpy as np
import struct
from datetime import datetime


import datastructures as ds


#Defining parser

class definedParser:
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


     def actualh5parser(self,timestamp,inputvalues,PackageNumber):
          # This method is here just for ilustation, it should be overriden by each instance of the class
          print ("Warning: This method has not been overriden properly!")


     def IterativeParsing(self,fileDescription):
         self.toplot=np.array([])
         self.datalength=np.array([])
         to5hparser=np.array([])
         leftvalues=''
         iterData=[]
         CompleteLine=True
         welcome=fileDescription.readline()
         print (welcome)
		 
         #"The following pat of the script reads lines from a structured data file and detects 
         #if a line is complete or not"
         for line in fileDescription.readlines():
             self.nReadLines=self.nReadLines+1
             print (repr(line))
             
             if CompleteLine is True:
                 iterData=''
                 a=line.index(self.PackageHeader)
                 b=line.index(self.TimeHeader)
                 c=line.index(self.DataHeader)
                 d=len(line)
                 
                 PackageNumber=int(''.join(line[a+5:b]))
                 timestamp=float(''.join(line[b+5:c]))
            
                #The line is not complete
                 if (line[-6:-1]!=self.EndHeader):
                      CompleteLine=False
                      print ('TRUE ->', CompleteLine, repr(line[-6:-1]), '->', self.EndHeader, 'HEADER->', repr(line[:5]))
                      iterData=line[c+5:]
          
                 else:
                      CompleteLine=True
                      print ('TRUE ->',CompleteLine, repr(line[-6:-1]), '->', self.EndHeader, 'HEADER->', repr(line[:5]))
                      iterData=line[c+5:-6]
                      datapackagelength=len(iterData)
                      print(self.package,'->', datetime.strftime("%b-%d-%Y -- %H:%M:%S",datetime.localtime(int(timestamp))), '->', PackageNumber, 'DATA LENGTH:', datapackagelength)
                      self.toplot=np.append(self.toplot,PackageNumber)
                      self.datalength=np.append(self.datalength, datapackagelength)
                      to5hparser=''.join([leftvalues, iterData])
                      leftvalues=self.actualh5parser(timestamp,to5hparser,PackageNumber)
                      self.package=self.package+1
            
             elif CompleteLine is False:
                  #line not complete yet
                  if (line[-6:-1]!=self.EndHeader):
                       CompleteLine=False
                       print ('FALSE ->', CompleteLine, repr(line[-6:-1]), '->', self.EndHeader, 'HEADER->', repr(line[:5]))
                       iterData+=line
            
                  # Line complete
                  else:
                        CompleteLine=True
                        print ('FALSE ->', CompleteLine, repr(line[-6:-1]), '->', self.EndHeader, 'HEADER->', repr(line[:5]))
                        iterData+=line[:-6]
                        datapackagelength=len(iterData)
                        print (self.package,'->', datetime.strftime("%b-%d-%Y -- %H:%M:%S",datetime.localtime(int(timestamp))), '->', PackageNumber, 'DATA LENGTH:', datapackagelength)
                        self.toplot=np.append(self.toplot,PackageNumber)
                        self.datalength=np.append(self.datalength, datapackagelength)
                        to5hparser=''.join([leftvalues, iterData])
                        leftvalues=self.actualh5parser(timestamp,to5hparser,PackageNumber)
                        self.package=self.package+1 
                        if self.package==2:
                              break
                        
         fileDescription.close()

 
class RadiometerParser(definedParser):
    def __init__(self, filedescription, sampleACT,sampleAMR, sampleSND, verbose):
        self.Packagenumber = 'PACR'
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
    

class ThermistorParser(definedParser):
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


class GPSParser(definedParser):
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


class DataFile:
    """
    This replaces py2 `CreateFile` and is an object primarily to avoid returning a 15-tuple of the rows, tables, and file.
    Since it's really just a data container for an open file, it's probably best to just delete it when finished.
    """
    def __init__(self, filename):
        self.h5file = tb.open_file(filename, 'w', title="Acquisition data")

        self.groups = {}
        self.tables = {}
        self.rows = {}
        self.create_tree()
        self._thermistor_metadata()  # Thermistor metadata copy-pasted from py2


    def __del__(self):
        self.close()


    def close(self):
        self.h5file.close()

    
    def _thermistor_metadata(self):
        # This is copy-pasted (and cleaned up a tiny bit) thermistor metadata.
        # Result is a numpy array. Each append() adds another value.
        infoRow = self.rows['IThermistors']
        infoRow['General'] = 'Coefficients from voltage to Temperatures for KS502J2 thermistors: A = 1.29337828808 * 10^-3,	B = 2.34313147501 * 10^-4,	C = 1.09840791237 * 10^-7,	D = -6.51108048031 * 10^-11'
        infoRow.append()
        infoRow['General'] = 'Coefficients from voltage to Temperatures for 44906 (the ones in the AMR) thermistors:  A = 1.28082086269172 * 10^-3,	B = 2.36865057309759 * 10^-4,	C = 0.902634799967035 * 10^-7,	D = 0'
        infoRow.append()
        infoRow['General'] = 'regulatedVoltage = 1.06, 	resist = (MeasuredVoltage / (regulatedVoltage - MeasuredVoltage)) * 5000'
        infoRow.append()
        infoRow['General'] = 'tempInv = (A + B * log(resist) + C * log(resist)^3 + D * log(resist)^5), temp = 1 / tempInv'
        infoRow.append()
        # All of these will need to be reassigned/checked.
        infoRow['General'] = '''
            thermistorName[0]="Pyramidal BaseRight" 
            thermistorName[1]="Pyramidal TopLeft" 
            thermistorName[2]="ABEB Case Top"
            thermistorName[3]="NC"
            thermistorName[4]="NC"
            thermistorName[5]="NC"
            thermistorName[6]="NC"
            thermistorName[7]="NC"
            thermistorName[8]="CalTar|Upper Left[1]"
            thermistorName[9]="CalTar|Lower Left[3]"
            thermistorName[10]="CalTar|Center[2]"
            thermistorName[11]="CalTar|Bottom Left[1]"
            thermistorName[12]="CalTar|Bottom Right[3]"
            thermistorName[13]="CalTar|Upper Right[3]"        
            thermistorName[14]="CalTar|Lower Right[1]"
            thermistorName[15]="CalTar|Top[2]"
            thermistorName[16]="?"
            thermistorName[17]="?"   
            thermistorName[18]="?"
            thermistorName[19]="?"
            thermistorName[20]="QH-18/24"
            thermistorName[21]="QV-18/24"
            thermistorName[22]="QV-34"
            thermistorName[23]="QH-34"
            thermistorName[24]="Power Chamber"
            thermistorName[25]="Power Chamber"
            thermistorName[26]="Paraboloid Middle"
            thermistorName[27]="Paraboloid Top" 
            thermistorName[28]="Paraboloid Bottom"
            thermistorName[29]="Motor Cavity"
            thermistorName[30]="Motor Cavity"
            thermistorName[31]="Motor Cavity"
            #The following thermistor names need to be filled with the correct locations after hardware installation
            thermistorName[32]="...."
            thermistorName[33]="...."
            thermistorName[34]="...."
            thermistorName[35]="...."
            thermistorName[36]="...."
            thermistorName[37]="...."
            thermistorName[38]="...."
            thermistorName[39]="...."
            thermistorName[40]="...." '''
        infoRow.append()
        self.tables['IThermistors'].flush()


    def create_tree(self) -> None:
        """
        Creates the structure (groups, tables, row pointers) of the .h5 file.
        This structure is saved in reference to dicts in self.
        """
        # Create structure (groups and tables)
        self.groups['R'] = self.h5file.create_group('/', 'Radiometric_Data', "Data from microwave (6 channels), millimeter-wave (3 channels), and sounders (16 channels), and motor position and computer time")
        self.tables['AMR'] = self.h5file.create_table(self.groups['R'], 'MW_Data', ds.AMRSample, "Radiometric data from AMR")
        self.tables['ACT'] = self.h5file.create_table(self.groups['R'], 'MMW_Data', ds.ACTSample, "Radiometric data from ACT")
        self.tables['SND'] = self.h5file.create_table(self.groups['R'], 'SND_Data', ds.SNDSample, "Radiometric data from SND")

        self.groups['T'] = self.h5file.create_group('/', 'Temperature_Data', "Thermistor readout and computer time")
        self.tables['THM'] = self.h5file.create_table(self.groups['T'], 'Thermistor_Data', ds.ThermistorSample, "System temperature in volts (5 kOhm thermistors)")

        self.groups['G'] = self.h5file.create_group('/', 'GPSIMU_Data', "Euler angles (roll, pitch, yaw) and position (lat, long, alt), and GPS time and computer time")
        self.tables['IMU'] = self.h5file.create_table(self.groups['G'], 'GPSIMU_Data', ds.IMUSample, "System position (lat, long), altitude, and GPS time")
        
        self.groups['I'] = self.h5file.create_group('/', 'Information', "README before reading file")
        self.tables['IGeneral'] = self.h5file.create_table(self.groups['I'], 'General_Info', ds.Information, "Raw files used for composing this .h5")
        self.tables['IServer'] = self.h5file.create_table(self.groups['I'], 'Server_Info', ds.Information, "JSON-formatted info regarding server")
        self.tables['IThermistors'] = self.h5file.create_table(self.groups['I'], 'Thermistors_Info', ds.Information, "Thermistor information")
        # Unused in py2
        # tableINFRadiometer = self.h5file.create_table(self.groups['I'], 'Radiometer_Info', ds.Information, "Radiometer information")
        # tableINFGPS = self.h5file.create_table(self.groups['I'], 'GPS_Info', ds.Information, "GPS-IMU information")

        # Create row pointers which hold data in dict format.
        self.rows['AMR'] = self.tables['AMR'].row
        self.rows['ACT'] = self.tables['ACT'].row
        self.rows['SND'] = self.tables['SND'].row
        self.rows['THM'] = self.tables['THM'].row
        self.rows['IMU'] = self.tables['IMU'].row

        self.rows['IServer'] = self.tables['IServer'].row
        self.rows['IGeneral'] = self.tables['IGeneral'].row
        self.rows['IThermistors'] = self.tables['IThermistors'].row


if __name__ == '__main__':
    f = DataFile("./test.h5")
    print("")


    f.close()