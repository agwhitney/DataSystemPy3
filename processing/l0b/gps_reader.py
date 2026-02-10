import tables as tb


class GPSReader:
    def __init__(self, filename):
        table = tb.open_file(filename, 'r').root.GPS_IMUData.GPSIMU_DATA

        self.package_number = table.col('Packagenumber').flatten()
        self.euler_angles = table.col('EulerAngles')
        self.position = table.col('Position')
        self.gps_time = table.col('GPSTime').flatten()
        self.timestamps = table.col('Timestamp').flatten()

    