from readergps import GPSReader
from readerrad import AMRReader
from readerthm import ThermistorReader

import tables as tb
from pathlib import Path


class Reader:
    def __init__(self, filename):
        self.filename = Path(filename).name
        file = tb.open_file(filename)

        data_thm = file.root.Temperature_Data.Thermistor_DATA
        data_gps = file.root.GPS_IMUData.GPSIMU_DATA
        data_rad = file.root.Radiometric_Data.MW_DATA

        self.radiometer = AMRReader(data_rad)
        self.gps = GPSReader(data_gps)
        self.thermistors = ThermistorReader(data_thm)

        try:
            self.thermistors.metatable = file.root.Temperature_Data.Thermistor_MAP
        except tb.NoSuchNodeError as e:
            print(e, "No thermistor metadata")
            self.thermistors.metatable = None



if __name__ == '__main__':
    r = Reader('processing/l0b/testln2.h5')
    r.thermistors.mean_sensors([4,5,6])