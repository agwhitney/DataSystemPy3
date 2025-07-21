"""
py2 ParserAux.py
"""

import tables as tb

import datastructures as ds



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
        infoRow['General'] = 'tempInv = (A + B * log(resist) + C * log(resist)**3 + D * log(resist)**5), temp = 1 / tempInv'
        infoRow.append()
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
            thermistorName[31]="Motor Cavity" '''
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