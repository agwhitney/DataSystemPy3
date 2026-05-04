import pandas as pd
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


    def get_calibration_point(self, index: int, thermistors: list[int], motor_start: int, motor_stop: int) -> tuple[float, pd.Series]:
        """
        Returns a tuple containing temperature and a radiometer row.
        Index is the row of the timestamp to use from the thermistors table.
        Counts is determined as the average between the motor start and stop positions.
        Temperature is determined as the average of the given thermistors.
        """
        subset = self.radiometer.data[
            (self.radiometer.data['Timestamp'] - self.thermistors.temps['Timestamp'][index] > 0)
            &
            (self.radiometer.data['Timestamp'] - self.thermistors.temps['Timestamp'][index+1] < 0)
        ]
        subset = subset[
            (subset['MotorPosition'] > motor_start)
            &
            (subset['MotorPosition'] < motor_stop)
        ]
        temperature = self.thermistors.temps[thermistors].mean(axis=1).iloc[index]
        return (temperature, subset.mean())