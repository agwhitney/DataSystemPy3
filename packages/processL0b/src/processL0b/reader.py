import tables as tb

from pathlib import Path

from .gpsreader import GPSReader
from .radreader import AMRReader
from .thmreader import ThermistorReader

class Reader:
    def __init__(self, filename: str):
        self.filename = Path(filename).name
        file = tb.open_file(filename)

        data_thm = file.root.Temperature_Data.Thermistor_DATA
        data_gps = file.root.GPS_IMUData.GPSIMU_DATA
        data_amr = file.root.Radiometric_Data.MW_DATA
        try:
            meta_thm = file.root.Temperature_Data.Thermistor_MAP
        except tb.NoSuchNodeError as e:
            print(e, "No thermistor metadata")
            meta_thm = None

        self.radiometer = AMRReader(data_amr)
        self.gps = GPSReader(data_gps)
        self.thermistors = ThermistorReader(data_thm, meta_thm)


    def correlate_timestamps(self):
        ...