import pandas as pd

from dataclasses import dataclass
from tables.table import Table as H5Table



@dataclass
class Channel:
    """The channel index is determined by the physical connection at the analog backend board."""
    index: int
    frequency: float  # GHz
    label: str


AMR_CHANNELS = [
    Channel(0, 34, '34 QV'),
    Channel(1, 0, 'Not Connected 1'),
    Channel(2, 18.7, '18 QV'),
    Channel(3, 23.8, '24 QV'),
    Channel(4, 34, '34 QH'),
    Channel(5, 0, 'Not Connected 2'),
    Channel(6, 18.7, '18 QH'),
    Channel(7, 23.8, '24 QH'),
]

SND_CHANNELS = [
    Channel(0, 118.75, '118p0'), 
    Channel(1, 119, '118p0_25'),
    Channel(2, 119.25, '118p0_5'), 
    Channel(3, 119.75, '118p1'), 
    Channel(4, 120.75, '118p2'), 
    Channel(5, 121.75, '118p3'),
    Channel(6, 122.75, '118p4'),
    Channel(7, 123.75, '118p5'),
    Channel(8, 182.31, '183m1'), 
    Channel(9, 181.31, '183m2'),
    Channel(10, 180.31, '183m3'), 
    Channel(11, 179.31, '183m4'), 
    Channel(12, 178.31, '183m5'), 
    Channel(13, 177.31, '183m6'),
    Channel(14, 176.31, '183m7'), 
    Channel(15, 175.31, '183m8'),
]



class AMRReader:
    def __init__(self, table: H5Table):
        self.channels = AMR_CHANNELS
        self.data : pd.DataFrame  # Created/populated below

        # Raw data from HDF5 file
        counts = table.col('Counts')
        motorpos = table.col('MotorPosition').flatten()  # Flattening helps with legacy-style size-1 data
        timestamp = table.col('Timestamp').flatten()

        df1 = pd.DataFrame({'Timestamp': timestamp, 'MotorPosition': motorpos})
        df2 = pd.DataFrame({ch.label: counts[:, ch.index] for ch in self.channels})
        self.data = pd.concat([df1, df2], axis=1)

        # Columns derived from raw data
        self.data = self.data.assign( Revolution = (self.data['MotorPosition'].diff() > 1000).groupby(bool).cumsum() )
