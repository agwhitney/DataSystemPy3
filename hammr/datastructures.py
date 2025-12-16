"""
py2 h5classes.py
The *Sample classes define the tables in the .h5 file.
"""
import csv
import tables as tb
from tables import IsDescription, UInt8Col, UInt16Col, Float64Col, StringCol

from utils import get_thermistor_map
from filepaths import PATH_TO_CONFIGS


class AMRSample(IsDescription):
    Counts		  = UInt16Col(8)     # Unsigned short integer         
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SystemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)     # Signed 64-bit integer


class ACTSample(IsDescription):
    Counts		  = UInt16Col(4)     # Unsigned short integer        
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SystemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)    # Signed 64-bit integer


class SNDSample(IsDescription):
    Counts	      = UInt16Col(16)    # Unsigned short integer      
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte        
    SystemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)    # Signed 64-bit integer


class ThermistorSample(IsDescription):
    Packagenumber = UInt16Col(1)
    Voltages      = Float64Col(40)     # Unsigned short integer
    Timestamp     = Float64Col(1)      # Signed 64-bit integer


class IMUSample(IsDescription):
    Packagenumber = UInt16Col(1)
    EulerAngles   = Float64Col(3)    
    Position      = Float64Col(3) 
    GPSTime       = Float64Col(1)
    Timestamp     = Float64Col(1)    


class Information(IsDescription):
    General       = StringCol(8192)


class ThermistorMap(IsDescription):
    Digitizer     = UInt8Col()
    Thermistor    = UInt8Col()
    Location      = StringCol(50)  # Description of thermistor's physical placement
    Model         = StringCol(20)  # Model number



class DataFile:
    """
    This replaces py2 `ParserAux.CreateFile` method. Creates an .h5 file.
    Py2 had a method returning a 15-tuple of rows, tables, and the file. This object 
    contains that info in dicts.
    """
    def __init__(self, filename):
        self.h5file = tb.open_file(filename, 'w', title="Acquisition data")

        self.groups = {}
        self.tables = {}
        self.rows = {}
        self.create_tree()
        self._thermistor_metadata()
        self.store_thermistor_map()


    def __del__(self):
        self._close()


    def _close(self) -> None:
        """Once the file is closed the groups/tables/rows become inaccessible (I think)"""
        self.h5file.close()

    
    def _thermistor_metadata(self) -> None:
        """
        This metadata fills the Thermistors metadata row. Strings with coefficients are copy/pasted and haven't been reviewed (9/4/25)
        `get_thermistor_map` refers to the file in the Config folder. TODO probably it shouldn't
        """
        infoRow = self.rows['IThermistors']
        infoRow['General'] = 'Coefficients from voltage to Temperatures for KS502J2 thermistors: A = 1.29337828808 * 10^-3,	B = 2.34313147501 * 10^-4,	C = 1.09840791237 * 10^-7,	D = -6.51108048031 * 10^-11'
        infoRow.append()
        infoRow['General'] = 'Coefficients from voltage to Temperatures for 44906 (the ones in the AMR) thermistors:  A = 1.28082086269172 * 10^-3,	B = 2.36865057309759 * 10^-4,	C = 0.902634799967035 * 10^-7,	D = 0'
        infoRow.append()
        infoRow['General'] = 'regulatedVoltage = 1.06, 	resist = (MeasuredVoltage / (regulatedVoltage - MeasuredVoltage)) * 5000'
        infoRow.append()
        infoRow['General'] = 'tempInv = (A + B * log(resist) + C * log(resist)^3 + D * log(resist)^5), temp = 1 / tempInv'
        infoRow.append()
        infoRow['General'] = get_thermistor_map()
        infoRow.append()
        self.tables['IThermistors'].flush()


    def store_thermistor_map(self) -> None:
        """Fills the /Information/Thermistors_CSV table with values from thermistors.csv in the config.
        TODO the config should be copied when the measurement runs so that L0a -> L0b can run separately.
        """
        path = PATH_TO_CONFIGS / 'thermistors.csv'
        if not path.exists:
            return  # TODO Handles above todo by doing nothing

        row = self.tables['IThermistorsCSV'].row
        with open(path, 'r', newline='') as file:
            reader = csv.reader(file, delimiter=',')
            for line in reader:
                if reader.line_num == 1:
                    continue
                row['Digitizer'] = int(line[0])
                row['Thermistor'] = int(line[1])
                row['Location'] = line[2]
                row['Model'] = line[3]
                row.append()
        self.tables['IThermistorsCSV'].flush()


    def create_tree(self) -> None:
        """
        Creates the structure (groups, tables, row pointers) of the .h5 file.
        Tables package lets you access these with dot notation, but I've stored them in dicts.
        """
        # Create structure (groups and tables)
        self.groups['R'] = self.h5file.create_group('/', 'Radiometric_Data', "Data from microwave (6 channels), millimeter-wave (3 channels), and sounders (16 channels), and motor position and computer time")
        self.tables['AMR'] = self.h5file.create_table(self.groups['R'], 'MW_DATA', AMRSample, "Radiometric data from AMR")
        self.tables['ACT'] = self.h5file.create_table(self.groups['R'], 'MMW_DATA', ACTSample, "Radiometric data from ACT")
        self.tables['SND'] = self.h5file.create_table(self.groups['R'], 'SND_DATA', SNDSample, "Radiometric data from SND")

        self.groups['T'] = self.h5file.create_group('/', 'Temperature_Data', "Thermistor readout and computer time")
        self.tables['THM'] = self.h5file.create_table(self.groups['T'], 'Thermistor_DATA', ThermistorSample, "System temperature in volts (5 kOhm thermistors)")

        self.groups['G'] = self.h5file.create_group('/', 'GPS_IMUData', "Euler angles (roll, pitch, yaw) and position (lat, long, alt), and GPS time and computer time")
        self.tables['IMU'] = self.h5file.create_table(self.groups['G'], 'GPSIMU_DATA', IMUSample, "System position (lat, long), altitude, and GPS time")
        
        self.groups['I'] = self.h5file.create_group('/', 'Information', "README before reading file")
        self.tables['IGeneral'] = self.h5file.create_table(self.groups['I'], 'General_INFO', Information, "Raw files used for composing this .h5")
        self.tables['IServer'] = self.h5file.create_table(self.groups['I'], 'Server_INFO', Information, "JSON-formatted info regarding server")
        self.tables['IThermistors'] = self.h5file.create_table(self.groups['I'], 'Thermistors_INFO', Information, "Thermistor information")
        self.tables['IThermistorsCSV'] = self.h5file.create_table(self.groups['I'], 'Thermistors_CSV', ThermistorMap, "Map of thermistor connection and location.")  # AGW new
        # These appear to be unused
        self.tables['IRadiometer'] = self.h5file.create_table(self.groups['I'], 'Radiometer_INFO', Information, "Radiometer information")
        self.tables['IGPS'] = self.h5file.create_table(self.groups['I'], 'GPS_INFO', Information, "GPS-IMU information")

        # Create row pointers which hold data in dict format.
        # This isn't strictly necessary, but it keeps the strict access within this file.
        self.rows['AMR'] = self.tables['AMR'].row
        self.rows['ACT'] = self.tables['ACT'].row
        self.rows['SND'] = self.tables['SND'].row
        self.rows['THM'] = self.tables['THM'].row
        self.rows['IMU'] = self.tables['IMU'].row

        self.rows['IServer'] = self.tables['IServer'].row
        self.rows['IGeneral'] = self.tables['IGeneral'].row
        self.rows['IThermistors'] = self.tables['IThermistors'].row  # Only used locally


if __name__ == '__main__':
    f = DataFile("./test.h5")
    print("debug breakpoint")


    f._close()