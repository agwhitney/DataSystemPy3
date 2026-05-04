import pandas as pd

from tables.table import Table as H5Table


class GPSReader:
    def __init__(self, table: H5Table):
        euler_angles = table.col('EulerAngles')
        position = table.col('Position')

        self.data = pd.DataFrame({
            'GPSTime': table.col('GPSTime').flatten(),
            'SystemTime': table.col('Timestamp').flatten(),
            'Latitude': position[:, 0],
            'Longitude': position[:, 1],
            'Altitude': position[:, 2],
            'Roll': euler_angles[:, 0],
            'Pitch': euler_angles[:, 1],
            'Yaw': euler_angles[:, 2],
        })

    
    def timedelta(self):
        return abs(self.gps_time - self.timestamp)