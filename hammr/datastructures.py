"""
py2 h5classes.py
"""
from tables import IsDescription, UInt8Col, UInt16Col, Float64Col, StringCol
import tables as tb

from utils import get_thermistor_map


class AMRSample(IsDescription):
    Counts		  = UInt16Col(8)     # Unsigned short integer         
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SytemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)     # Signed 64-bit integer


class ACTSample(IsDescription):
    Counts		  = UInt16Col(4)     # Unsigned short integer        
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SytemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)    # Signed 64-bit integer


class SNDSample(IsDescription):
    Counts	      = UInt16Col(16)    # Unsigned short integer      
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte        
    SytemStatus   = UInt8Col(1)      # unsigned byte
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



class DataFile:
    """
    This replaces py2 `CreateFile` and is an object primarily to avoid returning a 15-tuple of the rows, tables, and file.
    It's really just a data container for an open file.
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
        infoRow['General'] = get_thermistor_map()
        infoRow.append()
        self.tables['IThermistors'].flush()


    def create_tree(self) -> None:
        """
        Creates the structure (groups, tables, row pointers) of the .h5 file.
        This structure is saved in reference to dicts in self.
        """
        # Create structure (groups and tables)
        self.groups['R'] = self.h5file.create_group('/', 'Radiometric_Data', "Data from microwave (6 channels), millimeter-wave (3 channels), and sounders (16 channels), and motor position and computer time")
        self.tables['AMR'] = self.h5file.create_table(self.groups['R'], 'MW_Data', AMRSample, "Radiometric data from AMR")
        self.tables['ACT'] = self.h5file.create_table(self.groups['R'], 'MMW_Data', ACTSample, "Radiometric data from ACT")
        self.tables['SND'] = self.h5file.create_table(self.groups['R'], 'SND_Data', SNDSample, "Radiometric data from SND")

        self.groups['T'] = self.h5file.create_group('/', 'Temperature_Data', "Thermistor readout and computer time")
        self.tables['THM'] = self.h5file.create_table(self.groups['T'], 'Thermistor_Data', ThermistorSample, "System temperature in volts (5 kOhm thermistors)")

        self.groups['G'] = self.h5file.create_group('/', 'GPSIMU_Data', "Euler angles (roll, pitch, yaw) and position (lat, long, alt), and GPS time and computer time")
        self.tables['IMU'] = self.h5file.create_table(self.groups['G'], 'GPSIMU_Data', IMUSample, "System position (lat, long), altitude, and GPS time")
        
        self.groups['I'] = self.h5file.create_group('/', 'Information', "README before reading file")
        self.tables['IGeneral'] = self.h5file.create_table(self.groups['I'], 'General_Info', Information, "Raw files used for composing this .h5")
        self.tables['IServer'] = self.h5file.create_table(self.groups['I'], 'Server_Info', Information, "JSON-formatted info regarding server")
        self.tables['IThermistors'] = self.h5file.create_table(self.groups['I'], 'Thermistors_Info', Information, "Thermistor information")
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
    print("debug breakpoint")


    f.close()